"""Property-based test for category-tag rendering on post treatments.

# Feature: editorial-revamp, Property 1: Category tag is rendered on post treatments

Property 1 states: for any published post that has an assigned Category,
rendering that post's homepage card or hero treatment produces output
containing a distinguishable category tag labeled with that Category.

The homepage hero (``partials/editorial_hero.html``) and post card
(``partials/editorial_post_card.html``) both render the assigned Category as a
``.category-tag`` element whose visible label is the Category name. This test
generates published posts with varied Category names, renders each treatment,
and asserts the rendered output contains a ``.category-tag`` element labeled
with the assigned Category name.

Validates: Requirements 3.3
"""

import re

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.html import escape
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# Category names are rendered as the visible label of the tag. Constrain the
# generator to printable, non-control characters (letters, digits, spaces and
# common punctuation) so generated names model realistic editorial category
# labels while still exercising HTML-significant characters (&, <, >, ", ')
# which the template must escape. The name must contain at least one
# non-whitespace character so the tag has a meaningful label.
_name_alphabet = st.characters(
    min_codepoint=0x20,
    max_codepoint=0x7E,
    blacklist_categories=('Cc', 'Cs'),
)
category_names = (
    st.text(alphabet=_name_alphabet, min_size=1, max_size=80)
    .map(lambda s: s.strip())
    .filter(lambda s: len(s) > 0)
)

# Both homepage treatments that render a color-coded category tag.
TREATMENT_TEMPLATES = (
    'partials/editorial_post_card.html',
    'partials/editorial_hero.html',
)

# Captures the visible label of a `.category-tag` anchor. The class attribute
# may carry modifier classes (e.g. `category-tag category-tag--solid`).
_TAG_LABEL_RE = re.compile(
    r'class="category-tag[^"]*"[^>]*>(?P<label>.*?)</a>',
    re.DOTALL,
)


class CategoryTagRenderingProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='category-tag-author', password='test-password'
        )

    def _make_published_post(self, category):
        return Blog.objects.create(
            title='Category tag probe',
            slug='category-tag-probe',
            category=category,
            author=self.author,
            short_description='probe description',
            blog_body='<p>probe body</p>',
            status='published',
        )

    @settings(max_examples=25, deadline=None)
    @given(name=category_names)
    def test_category_tag_is_rendered_and_labeled(self, name):
        # Feature: editorial-revamp, Property 1: Category tag is rendered on
        # post treatments (Validates: Requirements 3.3)
        category = Category.objects.create(name=name)
        post = self._make_published_post(category)

        expected_label = escape(name)

        for template_name in TREATMENT_TEMPLATES:
            rendered = render_to_string(template_name, {'post': post})

            # A distinguishable category tag element must be present.
            labels = _TAG_LABEL_RE.findall(rendered)
            self.assertTrue(
                labels,
                msg=(
                    f'{template_name}: expected a .category-tag element for a '
                    f'published post with an assigned Category, found none.\n'
                    f'Rendered output:\n{rendered}'
                ),
            )

            # Exactly one category tag is expected on a single treatment, and it
            # must be labeled with the assigned Category name (HTML-escaped).
            self.assertEqual(
                len(labels),
                1,
                msg=(
                    f'{template_name}: expected exactly one .category-tag '
                    f'element, found {len(labels)}.'
                ),
            )
            self.assertEqual(
                labels[0],
                expected_label,
                msg=(
                    f'{template_name}: category tag label {labels[0]!r} does '
                    f'not match the assigned Category name {expected_label!r}.'
                ),
            )
