"""Property-based tests for SEO metadata preservation on the article detail page.

# Feature: editorial-revamp, Property 3: SEO metadata is preserved for every
# published post.

Property 3 states: for any published post, the rendered article detail page
contains each of the following metadata elements, verified individually:
canonical URL, Open Graph tags, Twitter Card tags, and JSON-LD structured data
(where JSON-LD is present).

The base layout (task 12.1) preserves the SEO blocks (canonical, og:*,
twitter:*, json_ld) and the article detail template overrides those blocks with
post-specific values. This test renders the detail page for generated published
posts and asserts each metadata element is present, checking every element
individually rather than as a single combined check (Requirement 13.7).

Validates: Requirements 5.2, 13.7
"""

import json
import re

from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# Titles and descriptions are drawn from printable text so the generators
# exercise varied, realistic content (including characters that must be escaped
# in HTML attributes and in the JSON-LD JS-string context) while staying within
# the model field limits (title<=200, short_description<=500, meta<=160).
title_strategy = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=0x2FFF),
    min_size=1,
    max_size=100,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

short_description_strategy = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=0x2FFF),
    min_size=1,
    max_size=200,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# meta_description is optional; when absent the templates fall back to a
# truncated short_description.
meta_description_strategy = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=0x2FFF),
        min_size=1,
        max_size=100,
    ).map(lambda s: s.strip()).filter(lambda s: len(s) > 0),
)


class Property3SeoMetadataPreservationTests(TestCase):
    """Property 3: SEO metadata is preserved for every published post.

    Validates: Requirements 5.2, 13.7
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='SEO Category')
        cls.author = User.objects.create_user(
            username='seo-author', password='test-password'
        )

    def _make_published_blog(self, *, title, short_description, meta_description):
        """Create a public Published_Blog.

        Saving with status='published' and no published_at makes Blog.save()
        stamp published_at to the current time, so the row is public (its
        Publication_Time is at or before now) and the detail view renders it
        normally rather than as a preview.
        """
        return Blog.objects.create(
            title=title,
            slug='seo-metadata-probe',
            category=self.category,
            author=self.author,
            short_description=short_description,
            blog_body='<p>Body content for SEO probe.</p>',
            status='published',
            meta_description=meta_description,
        )

    @settings(max_examples=25, deadline=None)
    @given(
        title=title_strategy,
        short_description=short_description_strategy,
        meta_description=meta_description_strategy,
    )
    def test_seo_metadata_is_preserved_for_every_published_post(
        self, title, short_description, meta_description
    ):
        # Feature: editorial-revamp, Property 3: SEO metadata is preserved for
        # every published post (Validates: Requirements 5.2, 13.7)
        post = self._make_published_blog(
            title=title,
            short_description=short_description,
            meta_description=meta_description,
        )

        url = reverse('Blog_detail', kwargs={'slug': post.slug})
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
            msg='published post detail page should render (200)',
        )
        html = response.content.decode('utf-8')

        # --- Canonical URL (verified individually) ---
        self.assertRegex(
            html,
            r'<link\s+rel="canonical"\s+href="[^"]+"',
            msg='canonical URL <link rel="canonical"> must be present',
        )

        # --- Open Graph tags (each verified individually) ---
        self.assertIn(
            'property="og:site_name"', html,
            msg='Open Graph og:site_name must be present',
        )
        self.assertIn(
            'property="og:title"', html,
            msg='Open Graph og:title must be present',
        )
        self.assertIn(
            'property="og:description"', html,
            msg='Open Graph og:description must be present',
        )
        # The detail template overrides og:type to "article".
        self.assertRegex(
            html,
            r'<meta\s+property="og:type"\s+content="article"',
            msg='Open Graph og:type must be "article" on the detail page',
        )
        self.assertIn(
            'property="og:url"', html,
            msg='Open Graph og:url must be present',
        )

        # --- Twitter Card tags (each verified individually) ---
        self.assertIn(
            'name="twitter:card"', html,
            msg='Twitter Card twitter:card must be present',
        )
        self.assertIn(
            'name="twitter:title"', html,
            msg='Twitter Card twitter:title must be present',
        )
        self.assertIn(
            'name="twitter:description"', html,
            msg='Twitter Card twitter:description must be present',
        )

        # --- JSON-LD structured data (where present, verified individually) ---
        json_ld_match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(
            json_ld_match,
            msg='JSON-LD <script type="application/ld+json"> block must be present',
        )
        # The JSON-LD must be well-formed JSON describing an Article.
        payload = json.loads(json_ld_match.group(1))
        self.assertEqual(
            payload.get('@context'), 'https://schema.org',
            msg='JSON-LD @context must be schema.org',
        )
        self.assertEqual(
            payload.get('@type'), 'Article',
            msg='JSON-LD @type must be Article',
        )
        self.assertIn(
            'headline', payload,
            msg='JSON-LD must carry the article headline',
        )
        self.assertIn(
            'author', payload,
            msg='JSON-LD must carry the article author',
        )
