"""Query-count regression tests for public listing and detail views.

Feature: editorial-revamp (Task 2.4)

These are deterministic example tests (NOT property-based). They guard
Requirement 13.2: the scheduling read-time filter added to
``Blog.objects.published()`` must not introduce additional per-row queries
on listing or detail views. In other words, the number of database queries a
public page issues must stay constant as the number of published rows grows
(no N+1 introduced by the scheduling filter).

Strategy: render a page with a small set of rows and capture the exact query
count, then render the same page with a substantially larger set of rows and
assert the query count is identical via ``assertNumQueries``. The
category-context cache is cleared before every measured request so the
per-request query cost is deterministic and comparable.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Blog, Category


def _make_published_blog(*, author, category, index, is_featured=False):
    """Create a public (published, past publication time) Blog.

    ``published_at`` is set to a fixed past instant so the row is
    unambiguously public under the read-time ``published()`` filter and the
    save() auto-stamp path is not exercised.
    """
    slug = f'query-count-post-{"featured" if is_featured else "listing"}-{index}'
    return Blog.objects.create(
        title=f'Query count post {index}',
        slug=slug,
        category=category,
        author=author,
        short_description='A post used for query-count regression testing.',
        blog_body='<p>Body</p>',
        status='published',
        published_at=timezone.now() - timedelta(days=1),
        is_featured=is_featured,
    )


class HomepageQueryCountRegressionTests(TestCase):
    """The homepage listing must not issue per-row queries as posts grow.

    Validates: Requirements 13.2
    """

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='query-count-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Query Count Topic')

    def _measure_baseline(self, url):
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_homepage_query_count_constant_as_posts_grow(self):
        url = reverse('home')

        # Small set: 3 non-featured published posts (page 1 renders all 3).
        for i in range(3):
            _make_published_blog(
                author=self.author, category=self.category, index=i
            )
        baseline = self._measure_baseline(url)

        # Larger set: grow to 10 non-featured published posts. Page 1 now
        # renders the full page size (6 cards), each rendering author and
        # category. With select_related in place the query count must not
        # grow relative to the 3-post baseline.
        for i in range(3, 10):
            _make_published_blog(
                author=self.author, category=self.category, index=i
            )

        cache.clear()
        with self.assertNumQueries(baseline):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class BlogDetailQueryCountRegressionTests(TestCase):
    """The article detail view must not issue per-row queries as the
    scheduling-filtered related-posts listing grows.

    Validates: Requirements 13.2
    """

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='detail-query-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Detail Query Topic')
        cls.post = Blog.objects.create(
            title='Detail target post',
            slug='detail-target-post',
            category=cls.category,
            author=cls.author,
            short_description='The article whose detail page is measured.',
            blog_body='<p>Body</p>',
            status='published',
            published_at=timezone.now() - timedelta(days=1),
        )

    def _measure_baseline(self, url):
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_detail_query_count_constant_as_related_posts_grow(self):
        url = reverse('Blog_detail', kwargs={'slug': self.post.slug})

        # Small set: 2 additional published posts in the same category feed
        # the "related posts" listing (which runs through published()).
        for i in range(2):
            _make_published_blog(
                author=self.author, category=self.category, index=i
            )
        baseline = self._measure_baseline(url)

        # Larger set: grow to 10 published posts in the category. The related
        # listing is capped at 3 and uses select_related, so the detail
        # view's query count must stay identical to the baseline.
        for i in range(2, 10):
            _make_published_blog(
                author=self.author, category=self.category, index=i
            )

        cache.clear()
        with self.assertNumQueries(baseline):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
