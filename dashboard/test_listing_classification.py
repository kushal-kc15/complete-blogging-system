"""Property-based test for dashboard post-listing state classification.

# Feature: editorial-revamp, Property 18: Dashboard listing classifies each
# post by its true state.

Property 18 states: for any Blog, the dashboard post listing labels it as
``draft``, ``scheduled``, or ``published`` matching its actual state (draft
when status is draft; scheduled when status is published with a future
``published_at``; published otherwise), and shows the Publication_Time for
scheduled posts.

The test renders the real dashboard posts view (``dashboard/posts.html``) as a
logged-in Editor holding ``blogs.view_blog`` and asserts, per rendered table
row, that the correct status pill is shown and that scheduled rows include
their ``published_at`` time.

Validates: Requirements 12.5
"""

import datetime as dt
import re

from django.contrib.auth.models import Permission, User
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from blogs.models import Blog, Category


# Fixed, timezone-aware reference "now". All scheduling offsets are applied
# relative to this instant and the clock is frozen here so classification is
# deterministic across examples.
REFERENCE = dt.datetime(2024, 6, 15, 12, 0, 0, tzinfo=dt.timezone.utc)

# Three true states a row can be in. The dashboard posts view paginates at 6
# rows per page, so each generated list is capped at 6 to keep every row on the
# first page under test.
STATES = ['draft', 'scheduled', 'published']


def _row_fragments(html):
    """Return the list of ``<tr>`` fragments inside the table body."""
    body_match = re.search(r'<tbody>(.*?)</tbody>', html, re.DOTALL)
    if not body_match:
        return []
    body = body_match.group(1)
    # Each row starts at a <tr>; drop the leading empty split segment.
    return [frag for frag in re.split(r'<tr\b', body)[1:]]


class Property18DashboardListingClassificationTests(TestCase):
    """Property 18: Dashboard listing classifies each post by its true state.

    Validates: Requirements 12.5
    """

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='listing-editor', password='test-password'
        )
        # The dashboard posts view is gated on ``blogs.view_blog``.
        cls.author.user_permissions.add(
            Permission.objects.get(codename='view_blog')
        )
        cls.category = Category.objects.create(name='Listing')

    def _make_blog(self, index, state):
        """Create a Blog in an exact true state.

        ``published_at`` is written directly with ``update()`` where needed so
        ``Blog.save()``'s auto-stamp does not perturb the intended state.
        """
        title = f'ListingProbe{index}'
        blog = Blog.objects.create(
            title=title,
            slug=f'listing-probe-{index}',
            category=self.category,
            author=self.author,
            short_description='probe',
            blog_body='<p>probe</p>',
            status='draft',
        )
        if state == 'draft':
            # Already a draft with published_at NULL.
            pass
        elif state == 'scheduled':
            # Published status with a future publication time.
            future = timezone.now() + dt.timedelta(days=3, seconds=index)
            Blog.objects.filter(pk=blog.pk).update(
                status='published', published_at=future
            )
        else:  # published
            # Published status, already live (published_at in the past).
            past = timezone.now() - dt.timedelta(days=3, seconds=index)
            Blog.objects.filter(pk=blog.pk).update(
                status='published', published_at=past
            )
        blog.refresh_from_db()
        return blog

    @settings(max_examples=25, deadline=None)
    @given(states=st.lists(st.sampled_from(STATES), min_size=1, max_size=6))
    def test_each_row_is_classified_by_its_true_state(self, states):
        # Feature: editorial-revamp, Property 18: Dashboard listing classifies
        # each post by its true state (Validates: Requirements 12.5)
        with freeze_time(REFERENCE):
            posts = [
                self._make_blog(index, state)
                for index, state in enumerate(states)
            ]

            self.client.force_login(self.author)
            response = self.client.get(reverse('posts'))
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()

            fragments = _row_fragments(html)
            self.assertEqual(
                len(fragments),
                len(posts),
                msg=f'expected {len(posts)} rows, found {len(fragments)}',
            )

            # Map each post's row fragment by its unique title.
            for post, state in zip(posts, states):
                row = next(
                    (f for f in fragments if post.title in f), None
                )
                self.assertIsNotNone(
                    row, msg=f'no row rendered for {post.title!r}'
                )

                if state == 'draft':
                    self.assertIn('status-pill--draft', row)
                    self.assertNotIn('status-pill--scheduled', row)
                    self.assertNotIn('status-pill--published', row)
                elif state == 'scheduled':
                    self.assertIn('status-pill--scheduled', row)
                    self.assertNotIn('status-pill--draft', row)
                    self.assertNotIn('status-pill--published', row)
                    # Scheduled rows must surface their Publication_Time.
                    expected_time = date_filter(
                        post.published_at, 'M j, Y, g:i a'
                    )
                    self.assertIn(
                        expected_time,
                        row,
                        msg=(
                            f'scheduled row for {post.title!r} must show its '
                            f'publication time {expected_time!r}'
                        ),
                    )
                else:  # published
                    self.assertIn('status-pill--published', row)
                    self.assertNotIn('status-pill--draft', row)
                    self.assertNotIn('status-pill--scheduled', row)
