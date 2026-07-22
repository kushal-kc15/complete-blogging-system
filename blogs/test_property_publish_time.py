"""Property-based tests for direct-publish publication-time recording.

Feature: editorial-revamp

These tests exercise the immediate-publish path of ``Blog.save()``:

    if self.status == 'published' and self.published_at is None:
        self.published_at = timezone.now()

The design reuses ``published_at`` as the Publication_Time carrier, so it is
important that saving a freshly-published post records the publication time
exactly once and that an already-recorded publication time is never
overwritten by a later save.
"""

import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from django.utils import timezone
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from blogs.models import Blog, Category


def _make_blog(*, status, published_at=None, title="A Post",
               short_description="A short description", is_featured=False):
    """Build (unsaved) a valid Blog with unique slug/author/category.

    Each call creates its own Category and author User with unique names so
    that generated examples never collide on the unique ``slug`` / unique
    ``Category.name`` constraints.
    """
    unique = uuid.uuid4().hex[:12]
    category = Category.objects.create(name=f"Cat-{unique}")
    author = User.objects.create_user(
        username=f"author-{unique}", password="test-password")
    return Blog(
        title=title or f"Title {unique}",
        slug=f"slug-{unique}",
        category=category,
        author=author,
        short_description=short_description or "desc",
        blog_body="<p>body</p>",
        status=status,
        is_featured=is_featured,
        published_at=published_at,
    )


# Text without null/control characters, which SQLite rejects in stored values.
_safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=120,
)


# Arbitrary tz-aware datetimes bounded to a sane range (avoids DB edge cases
# around the year 1/9999 while still spanning past and future relative to now).
_aware_datetimes = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(dt_timezone.utc),
)


class DirectPublishRecordsPublicationTimeOnceTest(HypothesisTestCase):
    """# Feature: editorial-revamp, Property 15: Direct publish records publication time once

    **Validates: Requirements 10.5**
    """

    @settings(max_examples=150, deadline=None)
    @given(
        title=_safe_text,
        short_description=_safe_text,
        is_featured=st.booleans(),
    )
    def test_publish_with_no_published_at_records_time_once(
            self, title, short_description, is_featured):
        # For any Blog saved with status 'published' and no existing
        # published_at, the save sets published_at to the current time.
        before = timezone.now()
        blog = _make_blog(
            status="published",
            published_at=None,
            title=title,
            short_description=short_description,
            is_featured=is_featured,
        )
        blog.save()
        after = timezone.now()

        blog.refresh_from_db()
        self.assertIsNotNone(blog.published_at)
        # Recorded time is the moment of the (first) save.
        self.assertGreaterEqual(blog.published_at, before)
        self.assertLessEqual(blog.published_at, after)

        # "...once": a subsequent save must not overwrite the recorded time.
        recorded = blog.published_at
        blog.title = (title + " edited")[:200]
        blog.save()
        blog.refresh_from_db()
        self.assertEqual(blog.published_at, recorded)

    @settings(max_examples=150, deadline=None)
    @given(
        existing=_aware_datetimes,
        status=st.sampled_from(["draft", "published"]),
        title=_safe_text,
    )
    def test_existing_published_at_is_never_overwritten(
            self, existing, status, title):
        # For any Blog that already has a published_at, saving does not
        # overwrite it (regardless of status, past or future).
        blog = _make_blog(
            status=status,
            published_at=existing,
            title=title,
        )
        blog.save()
        blog.refresh_from_db()
        self.assertEqual(blog.published_at, existing)

        # Saving again likewise preserves the original value.
        blog.short_description = "changed"
        blog.save()
        blog.refresh_from_db()
        self.assertEqual(blog.published_at, existing)
