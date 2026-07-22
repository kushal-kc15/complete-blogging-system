"""Property-based tests for read-time scheduled-publication visibility.

# Feature: editorial-revamp, Property 14: Publication visibility is a
# read-time comparison.

These tests exercise the ``Blog.objects.published()`` / ``scheduled()``
choke point that every public surface depends on. Publication visibility
must be a pure read-time comparison against the current time, with no
background task runner and no write required for a scheduled post to become
visible once its time passes.
"""

import datetime as dt

from django.contrib.auth.models import User
from django.utils import timezone
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# A fixed, timezone-aware reference "now" used as the evaluation time. Offsets
# are applied relative to this instant so Hypothesis can explore the boundary
# published_at == now as well as now ± epsilon.
REFERENCE = dt.datetime(2024, 6, 15, 12, 0, 0, tzinfo=dt.timezone.utc)


class Property14PublicationVisibilityTests(TestCase):
    """Property 14: Publication visibility is a read-time comparison.

    Validates: Requirements 10.2, 10.3, 11.1
    """

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='sched-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Scheduling')

    def _make_blog(self, *, status, published_at):
        return Blog.objects.create(
            title='Scheduled candidate',
            slug='scheduled-candidate',
            category=self.category,
            author=self.author,
            short_description='A scheduled candidate post.',
            blog_body='<p>Body</p>',
            status=status,
            published_at=published_at,
        )

    @settings(max_examples=25, deadline=None)
    @given(
        status=st.sampled_from(['draft', 'published']),
        # None exercises the null published_at branch; the tight range hits the
        # boundary (published_at == now and now ± a few seconds); the wide range
        # exercises clearly-past and clearly-future publication times.
        offset_seconds=st.one_of(
            st.none(),
            st.integers(min_value=-3, max_value=3),
            st.integers(min_value=-1_000_000, max_value=1_000_000),
        ),
    )
    def test_published_membership_matches_read_time_rule(self, status, offset_seconds):
        """A Blog is in published() iff status is 'published' and its
        published_at is null or at/ before the evaluation time."""
        if offset_seconds is None:
            requested_published_at = None
        else:
            requested_published_at = REFERENCE + dt.timedelta(seconds=offset_seconds)

        with freeze_time(REFERENCE):
            post = self._make_blog(
                status=status, published_at=requested_published_at
            )
            # Blog.save() may auto-stamp published_at for the immediate-publish
            # path, so evaluate the rule against the persisted value.
            post.refresh_from_db()
            now = timezone.now()
            stored_published_at = post.published_at
            expected_visible = post.status == 'published' and (
                stored_published_at is None or stored_published_at <= now
            )

            actual_visible = Blog.objects.published().filter(pk=post.pk).exists()

        self.assertEqual(
            actual_visible,
            expected_visible,
            msg=(
                f'status={post.status!r}, stored_published_at={stored_published_at!r}, '
                f'now={now!r}: expected published() membership {expected_visible}, '
                f'got {actual_visible}'
            ),
        )

    @settings(max_examples=25, deadline=None)
    @given(
        seconds_until_publish=st.integers(min_value=1, max_value=1_000_000),
        seconds_past_publish=st.integers(min_value=1, max_value=1_000_000),
    )
    def test_future_dated_row_becomes_visible_later_without_intervening_write(
        self, seconds_until_publish, seconds_past_publish
    ):
        """A future-dated published row is excluded now and becomes included at
        a later evaluation time, with no intervening write."""
        publish_at = REFERENCE + dt.timedelta(seconds=seconds_until_publish)
        later = publish_at + dt.timedelta(seconds=seconds_past_publish)

        # Create the row while "now" is before its publication time.
        with freeze_time(REFERENCE):
            post = self._make_blog(status='published', published_at=publish_at)
            self.assertFalse(
                Blog.objects.published().filter(pk=post.pk).exists(),
                msg='Future-dated post must be excluded before its publish time.',
            )
            self.assertTrue(
                Blog.objects.scheduled().filter(pk=post.pk).exists(),
                msg='Future-dated post must be classified as scheduled.',
            )

        # No write happens between the two evaluations: only the read-time
        # clock advances past the publication time.
        with freeze_time(later):
            self.assertTrue(
                Blog.objects.published().filter(pk=post.pk).exists(),
                msg='Post must become visible once its publish time passes.',
            )
            self.assertFalse(
                Blog.objects.scheduled().filter(pk=post.pk).exists(),
                msg='Post must no longer be scheduled once its time has passed.',
            )
