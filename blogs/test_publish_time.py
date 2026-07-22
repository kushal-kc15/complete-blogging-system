"""Property-based tests for direct-publish publication-time recording.

Feature: editorial-revamp
Property 15: Direct publish records publication time once.
"""

from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.utils import timezone

from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# Aware datetimes constrained to a sane range so DB storage never overflows
# and the read-time comparison stays unambiguous around any boundary.
_AWARE_DATETIMES = st.datetimes(
    min_value=timezone.datetime(2000, 1, 1),
    max_value=timezone.datetime(2100, 1, 1),
    timezones=st.just(dt_timezone.utc),
)


class DirectPublishPublicationTimeTests(TestCase):
    """Property 15: Direct publish records publication time once.

    Validates: Requirements 10.5
    """

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username="publish-time-author", password="test-password"
        )
        cls.category = Category.objects.create(name="Publish Time Topic")

    def _build_blog(self, *, status, published_at):
        return Blog(
            title="Publication time post",
            slug="publication-time-post",
            category=self.category,
            author=self.author,
            short_description="A short description",
            blog_body="<p>Body</p>",
            status=status,
            published_at=published_at,
        )

    # Feature: editorial-revamp, Property 15: Direct publish records
    # publication time once - save() sets published_at when publishing with
    # none set, and never overwrites an existing published_at.
    @settings(max_examples=25, deadline=None)
    @given(
        status=st.sampled_from(["draft", "published"]),
        preset_published_at=st.one_of(st.none(), _AWARE_DATETIMES),
    )
    def test_direct_publish_records_publication_time_once(
        self, status, preset_published_at
    ):
        blog = self._build_blog(status=status, published_at=preset_published_at)

        before = timezone.now()
        blog.save()
        after = timezone.now()

        blog.refresh_from_db()

        if preset_published_at is not None:
            # An existing published_at is never overwritten, regardless of status.
            self.assertEqual(blog.published_at, preset_published_at)
        elif status == "published":
            # Publishing with none set records the current time exactly once.
            self.assertIsNotNone(blog.published_at)
            self.assertGreaterEqual(blog.published_at, before)
            self.assertLessEqual(blog.published_at, after)
        else:
            # A draft with no publication time stays unpublished.
            self.assertIsNone(blog.published_at)

    # Feature: editorial-revamp, Property 15: Direct publish records
    # publication time once - a subsequent save must not overwrite the
    # publication time that the first publish recorded.
    @settings(max_examples=25, deadline=None)
    @given(preset_published_at=st.one_of(st.none(), _AWARE_DATETIMES))
    def test_resaving_published_blog_does_not_overwrite_publication_time(
        self, preset_published_at
    ):
        blog = self._build_blog(status="published", published_at=preset_published_at)
        blog.save()

        recorded = blog.published_at
        self.assertIsNotNone(recorded)

        # Re-saving an already-published blog leaves published_at untouched.
        blog.save()
        blog.refresh_from_db()

        self.assertEqual(blog.published_at, recorded)
