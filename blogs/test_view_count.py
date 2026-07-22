"""Property-based tests for article-detail view-count increment behavior.

# Feature: editorial-revamp, Property 19: View count increments once per
# non-preview read.

Property 19 states: for any Published_Blog, issuing ``N`` non-preview article
detail requests increases its view count by exactly ``N``, while any preview
request (draft or scheduled, by an authorized previewer) increases it by ``0``,
regardless of scheduling.

The view-count rule lives in ``BlogDetail`` (``blogs/views.py``), which gates
the increment on ``not is_preview``. A post is a preview when it is not public
(a draft, or a Scheduled_Blog whose ``published_at`` is still in the future).
``now`` is frozen with freezegun so the scheduling comparison is deterministic.

Validates: Requirements 13.1
"""

import datetime as dt

from django.contrib.auth.models import Permission, User
from django.test import Client
from django.urls import reverse
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# A fixed, timezone-aware reference "now". Scheduled posts are offset relative
# to this instant so the read-time scheduling comparison is fully deterministic.
REFERENCE = dt.datetime(2024, 6, 15, 12, 0, 0, tzinfo=dt.timezone.utc)


class Property19ViewCountIncrementTests(TestCase):
    """Property 19: View count increments once per non-preview read.

    Validates: Requirements 13.1
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='View Count')
        cls.author = User.objects.create_user(
            username='vc-author', password='test-password'
        )
        cls.staff = User.objects.create_user(
            username='vc-staff', password='test-password', is_staff=True
        )
        cls.editor = User.objects.create_user(
            username='vc-editor', password='test-password'
        )
        cls.editor.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='blogs', codename='change_blog'
            )
        )

    def _make_blog(self, *, status, published_at):
        """Create a Blog with an exact status/published_at pair.

        ``Blog.save()`` only auto-stamps ``published_at`` when a published row
        has none, and never overwrites an existing value, so passing an explicit
        ``published_at`` reliably produces a Scheduled_Blog when it is future.
        """
        return Blog.objects.create(
            title='View count probe',
            slug='view-count-probe',
            category=self.category,
            author=self.author,
            short_description='probe',
            blog_body='<p>probe</p>',
            status=status,
            published_at=published_at,
        )

    @settings(max_examples=25, deadline=None)
    @given(
        n_requests=st.integers(min_value=1, max_value=6),
        # None -> published with no published_at (public); negative -> already
        # due. Both are public (non-preview) reads.
        past_offset_seconds=st.one_of(
            st.none(),
            st.integers(min_value=-1_000_000, max_value=-1),
        ),
    )
    def test_non_preview_requests_increment_once_each(
        self, n_requests, past_offset_seconds
    ):
        # Feature: editorial-revamp, Property 19: View count increments once per
        # non-preview read (Validates: Requirements 13.1)
        if past_offset_seconds is None:
            published_at = None
        else:
            published_at = REFERENCE + dt.timedelta(seconds=past_offset_seconds)

        with freeze_time(REFERENCE):
            post = self._make_blog(status='published', published_at=published_at)
            start_views = post.views
            url = reverse('Blog_detail', kwargs={'slug': post.slug})

            # Anonymous reads of a public post are non-preview reads.
            client = Client()
            for _ in range(n_requests):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)

            post.refresh_from_db()

        self.assertEqual(
            post.views - start_views,
            n_requests,
            msg=(
                f'expected view count to rise by exactly {n_requests} for '
                f'{n_requests} non-preview reads, but it rose by '
                f'{post.views - start_views}'
            ),
        )

    @settings(max_examples=25, deadline=None)
    @given(
        n_requests=st.integers(min_value=1, max_value=6),
        # 'draft' is never public; 'scheduled' is published with a future time.
        post_kind=st.sampled_from(['draft', 'scheduled']),
        viewer_kind=st.sampled_from(['author', 'staff', 'editor']),
        future_offset_seconds=st.integers(min_value=1, max_value=1_000_000),
    )
    def test_authorized_preview_requests_do_not_increment(
        self, n_requests, post_kind, viewer_kind, future_offset_seconds
    ):
        # Feature: editorial-revamp, Property 19: View count increments once per
        # non-preview read (Validates: Requirements 13.1)
        if post_kind == 'draft':
            status = 'draft'
            published_at = None
        else:  # scheduled: published status, future publication time
            status = 'published'
            published_at = REFERENCE + dt.timedelta(seconds=future_offset_seconds)

        viewer = {
            'author': self.author,
            'staff': self.staff,
            'editor': self.editor,
        }[viewer_kind]

        with freeze_time(REFERENCE):
            post = self._make_blog(status=status, published_at=published_at)
            start_views = post.views
            url = reverse('Blog_detail', kwargs={'slug': post.slug})

            client = Client()
            client.force_login(viewer)
            for _ in range(n_requests):
                response = client.get(url)
                # An authorized previewer can view the non-public post.
                self.assertEqual(
                    response.status_code,
                    200,
                    msg=(
                        f'{viewer_kind} should be able to preview a {post_kind} '
                        f'post, got status {response.status_code}'
                    ),
                )

            post.refresh_from_db()

        self.assertEqual(
            post.views - start_views,
            0,
            msg=(
                f'a {post_kind} preview viewed by {viewer_kind} must not '
                f'increment the view count, but it rose by '
                f'{post.views - start_views}'
            ),
        )
