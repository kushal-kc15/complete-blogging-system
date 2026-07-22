"""Deterministic example tests for the homepage hero / featured empty-state.

# Feature: editorial-revamp

These are example (not property-based) tests covering the two observable
homepage behaviors defined by Requirements 3.1 and 3.4:

- Requirement 3.1: when at least one featured Published_Blog exists, the
  homepage renders exactly one large hero treatment for the primary featured
  post above all other listings.
- Requirement 3.4: when no Published_Blog is marked as featured, the homepage
  renders a named featured empty-state ("No featured story yet") instead of a
  hero, regardless of whether other non-featured Published_Blog posts exist.

The homepage template (``templates/home.html``) includes
``partials/editorial_hero.html`` (which renders ``.hero``) when
``featured_post`` is non-empty, otherwise it renders a named ``.empty-state``.
The ``home`` view selects featured posts via the ``is_featured`` flag against
``Blog.objects.published()``.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Blog, Category


class HeroPresenceTests(TestCase):
    """Requirement 3.1: hero renders when a featured published post exists."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='hero-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Editorial')

    def _make_post(self, *, slug, title, is_featured, status='published'):
        return Blog.objects.create(
            title=title,
            slug=slug,
            category=self.category,
            author=self.author,
            short_description='A short description for the post.',
            blog_body='<p>Body content.</p>',
            status=status,
            is_featured=is_featured,
        )

    def test_hero_renders_when_featured_post_exists(self):
        """A featured, published post produces exactly one hero treatment and
        no featured empty-state."""
        self._make_post(
            slug='featured-lead', title='The Featured Lead Story',
            is_featured=True,
        )

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # The hero partial renders an <article class="hero ...">.
        self.assertContains(response, '<article class="hero')
        # Exactly one hero treatment above all other listings. Counting the
        # hero's opening <article> tag avoids matching BEM sub-element classes
        # like `hero__content`/`hero__title` that also start with `hero`.
        self.assertEqual(content.count('<article class="hero'), 1)
        # The featured post's title appears in the hero.
        self.assertContains(response, 'The Featured Lead Story')
        # The named featured empty-state must NOT be present.
        self.assertNotContains(response, 'No featured story yet')


class FeaturedEmptyStateTests(TestCase):
    """Requirement 3.4: named empty-state renders when nothing is featured."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='empty-author', password='test-password'
        )
        cls.category = Category.objects.create(name='Editorial')

    def _make_post(self, *, slug, title, is_featured, status='published'):
        return Blog.objects.create(
            title=title,
            slug=slug,
            category=self.category,
            author=self.author,
            short_description='A short description for the post.',
            blog_body='<p>Body content.</p>',
            status=status,
            is_featured=is_featured,
        )

    def test_empty_state_renders_when_no_post_is_featured(self):
        """With only non-featured published posts, the homepage renders the
        named featured empty-state instead of a hero (Requirement 3.4)."""
        self._make_post(
            slug='regular-one', title='A Regular Published Post',
            is_featured=False,
        )
        self._make_post(
            slug='regular-two', title='Another Regular Published Post',
            is_featured=False,
        )

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Named featured empty-state is present...
        self.assertContains(response, 'No featured story yet')
        # ...and NO hero treatment is rendered, even though non-featured
        # published posts exist.
        self.assertEqual(content.count('<article class="hero'), 0)
