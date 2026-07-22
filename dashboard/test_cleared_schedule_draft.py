"""Unit tests for cleared-schedule-to-draft normalization in ``BlogForm``.

Feature: editorial-revamp
Task 4.3 — deterministic unit test for Requirement 12.4:

    WHEN an Editor clears a Blog's scheduled Publication_Time without setting
    status to published, THE Dashboard SHALL save the Blog as a draft rather
    than leaving it in an ambiguous scheduled state.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from blogs.models import Blog, Category
from dashboard.forms import BlogForm


class ClearedScheduleToDraftTests(TestCase):
    """Requirement 12.4: clearing the Publication_Time without publishing
    normalizes the post to a draft (published_at cleared)."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username="cleared-schedule-author", password="test-password"
        )
        cls.category = Category.objects.create(name="Scheduling Topic")

    def _make_scheduled_blog(self):
        """Create a Scheduled_Blog: status published with a future published_at."""
        future = timezone.now() + timedelta(days=3)
        return Blog.objects.create(
            title="Scheduled post",
            slug="scheduled-post",
            category=self.category,
            author=self.author,
            short_description="A short description",
            blog_body="<p>Body</p>",
            status="published",
            published_at=future,
        )

    def _form_data(self, *, status, publication_time=""):
        return {
            "title": "Scheduled post",
            "category": self.category.pk,
            "featured_image_alt": "",
            "short_description": "A short description",
            "blog_body": "<p>Body</p>",
            "status": status,
            "meta_description": "",
            "publication_time": publication_time,
        }

    def test_clearing_schedule_without_publishing_saves_as_draft(self):
        """Editing a Scheduled_Blog, clearing the Publication_Time, and leaving
        status as draft saves the post as a draft with no published_at."""
        blog = self._make_scheduled_blog()

        form = BlogForm(
            data=self._form_data(status="draft", publication_time=""),
            instance=blog,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

        saved = form.save()
        saved.refresh_from_db()

        self.assertEqual(saved.status, "draft")
        self.assertIsNone(saved.published_at)

    def test_cleared_schedule_is_not_left_in_scheduled_state(self):
        """After clearing the schedule without publishing, the post must not
        remain a Scheduled_Blog (published status with a future published_at)."""
        blog = self._make_scheduled_blog()
        self.assertEqual(Blog.objects.scheduled().count(), 1)

        form = BlogForm(
            data=self._form_data(status="draft", publication_time=""),
            instance=blog,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
        form.save()

        # No longer scheduled and not visible as a Published_Blog either.
        self.assertEqual(Blog.objects.scheduled().count(), 0)
        self.assertFalse(Blog.objects.published().filter(pk=blog.pk).exists())
