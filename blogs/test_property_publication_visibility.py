"""Property-based tests for scheduled-publishing read-time visibility.

# Feature: editorial-revamp, Property 14: Publication visibility is a read-time comparison

Property 14 states: for any Blog and any evaluation time ``t``, the Blog is
included in ``Blog.objects.published()`` (and therefore visible on every
Public_Surface) if and only if its status is ``published`` and its
Publication_Time (``published_at``) is null or at or before ``t``. A Blog with
a future Publication_Time is excluded at time ``t`` and becomes included at any
later evaluation time past its Publication_Time, with no intervening write.

Validates: Requirements 10.2, 10.3, 11.1
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# A fixed reference instant used as the origin for all generated offsets. Being
# tz-aware (UTC) matches the project's USE_TZ=True / TIME_ZONE='UTC' setup so the
# read-time comparison in published() is unambiguous around the boundary.
BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)

# Offsets (in seconds) relative to BASE. The range spans well before and well
# after BASE so both "already due" and "future scheduled" rows are generated.
offset_seconds = st.integers(min_value=-1_000_000, max_value=1_000_000)

# published_at is either genuinely NULL or a concrete instant at BASE + offset.
published_at_offsets = st.one_of(st.none(), offset_seconds)

statuses = st.sampled_from(['draft', 'published'])

# Small epsilons (seconds) used to probe the exact boundary published_at == now
# as well as now +/- epsilon.
epsilons = st.sampled_from([-1, 0, 1])


def _expected_visible(status, published_at, now):
    """Plain-Python oracle mirroring the published() predicate."""
    return status == 'published' and (
        published_at is None or published_at <= now
    )


class PublicationVisibilityReadTimeProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Visibility Category')
        cls.author = User.objects.create_user(
            username='visibility-author', password='test-password'
        )

    def _make_blog(self, status, published_at):
        """Create a Blog with an exact status/published_at.

        ``Blog.save()`` auto-stamps ``published_at`` when a row is published
        without one. To exercise every combination the property covers
        (including a genuinely NULL published_at on a published row), the exact
        value is written with a queryset ``update()`` that bypasses ``save()``.
        """
        blog = Blog.objects.create(
            title='Visibility probe',
            slug='visibility-probe',
            category=self.category,
            author=self.author,
            short_description='probe',
            blog_body='<p>probe</p>',
            status='draft',
        )
        Blog.objects.filter(pk=blog.pk).update(
            status=status, published_at=published_at
        )
        return blog.pk

    @settings(max_examples=200)
    @given(
        status=statuses,
        pub_offset=published_at_offsets,
        eval_offset=offset_seconds,
        eps=epsilons,
    )
    def test_publication_visibility_is_read_time_comparison(
        self, status, pub_offset, eval_offset, eps
    ):
        # Feature: editorial-revamp, Property 14: Publication visibility is a
        # read-time comparison (Validates: Requirements 10.2, 10.3, 11.1)
        published_at = (
            None if pub_offset is None else BASE + timedelta(seconds=pub_offset)
        )

        # Choose the evaluation instant. When published_at is concrete, anchor
        # the evaluation time to the boundary (published_at + eps) so the exact
        # published_at == now case and now +/- epsilon are exercised; otherwise
        # use an independent evaluation offset.
        if published_at is not None:
            now = published_at + timedelta(seconds=eps)
        else:
            now = BASE + timedelta(seconds=eval_offset)

        pk = self._make_blog(status, published_at)

        expected = _expected_visible(status, published_at, now)

        with freeze_time(now):
            actual = Blog.objects.published().filter(pk=pk).exists()

        self.assertEqual(
            actual,
            expected,
            msg=(
                f'status={status!r} published_at={published_at} now={now} '
                f'expected visible={expected} but got {actual}'
            ),
        )

    @settings(max_examples=200)
    @given(
        future_offset=st.integers(min_value=1, max_value=1_000_000),
        later_gap=st.integers(min_value=1, max_value=1_000_000),
    )
    def test_future_scheduled_row_becomes_visible_later_without_a_write(
        self, future_offset, later_gap
    ):
        # Feature: editorial-revamp, Property 14: Publication visibility is a
        # read-time comparison (Validates: Requirements 10.2, 10.3, 11.1)
        publication_time = BASE + timedelta(seconds=future_offset)
        before = publication_time - timedelta(seconds=1)
        at_or_after = publication_time + timedelta(seconds=later_gap - 1)

        pk = self._make_blog('published', publication_time)

        # Before its Publication_Time the scheduled row is excluded.
        with freeze_time(before):
            self.assertFalse(
                Blog.objects.published().filter(pk=pk).exists(),
                msg='future-dated row must be excluded before its time',
            )

        # At or after its Publication_Time it is included on the next read,
        # with no intervening write to the row.
        with freeze_time(at_or_after):
            self.assertTrue(
                Blog.objects.published().filter(pk=pk).exists(),
                msg='row must become visible once its time has passed',
            )
