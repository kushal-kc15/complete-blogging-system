"""Example tests: sitemap and RSS exclude scheduled posts.

These are deterministic example tests (not property-based) that verify the two
public syndication surfaces route through ``Blog.objects.published()`` and thus
exclude Scheduled_Blog posts (published-status rows whose ``published_at`` is
still in the future) while continuing to include ordinary published posts.

Validates: Requirements 11.2 (sitemap exclusion via ``BlogSitemap``) and
11.3 (RSS exclusion via ``LatestPostsFeed``).
"""

import datetime as dt

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from blog_main.feeds import LatestPostsFeed
from blog_main.sitemaps import BlogSitemap

from .models import Blog, Category


class SitemapRssScheduledExclusionTests(TestCase):
    """Scheduled posts must not leak into the sitemap or the RSS feed."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='syndication-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Syndication')

        now = timezone.now()

        # A genuinely public, published post (published_at in the past).
        cls.public_post = Blog.objects.create(
            title='Public post',
            slug='public-post',
            category=cls.category,
            author=cls.author,
            short_description='A public, already-published post.',
            blog_body='<p>Public body</p>',
            status='published',
            published_at=now - dt.timedelta(days=1),
        )

        # A scheduled post: status published but published_at is in the future.
        cls.scheduled_post = Blog.objects.create(
            title='Scheduled post',
            slug='scheduled-post',
            category=cls.category,
            author=cls.author,
            short_description='A scheduled, not-yet-due post.',
            blog_body='<p>Scheduled body</p>',
            status='published',
            published_at=now + dt.timedelta(days=7),
        )

    def test_sitemap_excludes_scheduled_post(self):
        """BlogSitemap.items() includes the public post and excludes the
        scheduled post (Requirement 11.2)."""
        item_pks = {blog.pk for blog in BlogSitemap().items()}

        self.assertIn(
            self.public_post.pk,
            item_pks,
            msg='Public post must appear in the sitemap.',
        )
        self.assertNotIn(
            self.scheduled_post.pk,
            item_pks,
            msg='Scheduled post must NOT appear in the sitemap.',
        )

    def test_rss_feed_excludes_scheduled_post(self):
        """LatestPostsFeed.items() includes the public post and excludes the
        scheduled post (Requirement 11.3)."""
        item_pks = {blog.pk for blog in LatestPostsFeed().items()}

        self.assertIn(
            self.public_post.pk,
            item_pks,
            msg='Public post must appear in the RSS feed.',
        )
        self.assertNotIn(
            self.scheduled_post.pk,
            item_pks,
            msg='Scheduled post must NOT appear in the RSS feed.',
        )
