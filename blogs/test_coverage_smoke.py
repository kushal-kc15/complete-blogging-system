"""Coverage smoke tests across every covered page in both themes.

Task 14.3 — Editorial Revamp. These are DETERMINISTIC smoke tests (not
property-based). They render every page covered by the redesign in both the
light and dark theme and assert three things per page:

1. The page extends the themed base — i.e. the Design System stylesheet
   (``editorial.css``) and the pre-paint theme resolver (``theme-init.js``)
   are both present in the rendered output. Every covered template extends
   ``base.html`` (Requirements 2.1, 5.1).
2. The page renders without depending on the removed Bootstrap 5 utility
   classes (``col-md-``, ``btn-primary``, ``navbar``, ``card-body``,
   ``row g-``). An equivalent layout is rendered under the new Design System
   instead (Requirement 5.3).
3. Dashboard listing pages use the density component set (``.data-table``),
   the compact-table presentation that is distinct from the spacious public
   reading pages (Requirement 5.4).

"Both themes" is simulated by requesting each page with and without a
``theme=dark`` cookie. The server renders the same HTML regardless (the theme
is applied client-side via ``[data-theme]`` driven by the ``theme`` cookie and
``theme-init.js``), so the assertions must hold identically in both cases.

Validates: Requirements 2.1, 5.1, 5.3, 5.4
"""

import re

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Blog, Category, Comment, Contact, Follow


# The Bootstrap utility classes the redesign removed. Each is matched as a
# whole CSS-class token so legitimate Design System classes that merely share
# a substring (e.g. ``post-card__body``, ``site-nav``, ``btn--primary``,
# ``container-wide``) never trigger a false positive. The lookbehind rejects a
# preceding word char or hyphen; the lookahead (where used) rejects a trailing
# one.
REMOVED_BOOTSTRAP_PATTERNS = {
    'col-md-': re.compile(r'(?<![\w-])col-md-'),
    'btn-primary': re.compile(r'(?<![\w-])btn-primary(?![\w-])'),
    'navbar': re.compile(r'(?<![\w-])navbar(?![\w-])'),
    'card-body': re.compile(r'(?<![\w-])card-body(?![\w-])'),
    'row g-': re.compile(r'(?<![\w-])row g-'),
}

# The two theme presentations. ``None`` = no cookie (light / system default),
# ``'dark'`` = an explicit dark Theme_Preference cookie. The server output is
# identical in both; asserting in both proves the themed base is theme-agnostic
# at the server layer (Requirement 2.1).
THEME_COOKIES = (None, 'dark')


class CoverageSmokeTestBase(TestCase):
    """Shared fixtures: one author, one editor (superuser), a follower reader,
    a published/featured post with a comment, and a contact message so every
    covered listing page renders real rows rather than an empty state."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Editorial Coverage')

        cls.author = User.objects.create_user(
            username='coverage-author', password='pw', email='author@example.com'
        )
        # A superuser is an Editor for every dashboard page and drives the
        # density branch of the author profile (Requirements 5.4, 5.6).
        cls.editor = User.objects.create_superuser(
            username='coverage-editor', password='pw', email='editor@example.com'
        )
        # A plain reader that follows the author, so the Following_Feed renders
        # a populated grid rather than its empty state.
        cls.reader = User.objects.create_user(
            username='coverage-reader', password='pw', email='reader@example.com'
        )

        cls.post = Blog.objects.create(
            title='Editorial coverage probe',
            slug='editorial-coverage-probe',
            category=cls.category,
            author=cls.author,
            short_description='A probe post used by the coverage smoke tests.',
            blog_body='<p>Coverage probe body content.</p>',
            status='published',
            is_featured=True,
            published_at=timezone.now(),
        )

        Comment.objects.create(
            user=cls.reader, blog=cls.post, comment='A coverage probe comment.'
        )
        Contact.objects.create(
            name='Coverage Probe',
            email='probe@example.com',
            subject='Coverage probe subject',
            message='Coverage probe message body.',
        )
        Follow.objects.create(follower=cls.reader, followed=cls.author)

    # --- assertion helpers ------------------------------------------------

    def _assert_themed_base(self, html, *, label, theme):
        detail = f'[{label}, theme={theme or "light"}]'
        self.assertIn(
            'editorial.css', html,
            msg=f'{detail} page does not load the themed Design System '
                f'stylesheet (editorial.css); it may not extend base.html.',
        )
        self.assertIn(
            'theme-init.js', html,
            msg=f'{detail} page does not include the pre-paint theme resolver '
                f'(theme-init.js); it may not extend the themed base.',
        )

    def _assert_no_removed_bootstrap(self, html, *, label, theme):
        detail = f'[{label}, theme={theme or "light"}]'
        offenders = [
            name for name, pattern in REMOVED_BOOTSTRAP_PATTERNS.items()
            if pattern.search(html)
        ]
        self.assertFalse(
            offenders,
            msg=f'{detail} still references removed Bootstrap utility '
                f'class(es): {", ".join(offenders)}. Render an equivalent '
                f'layout under the Design System instead (Requirement 5.3).',
        )

    def _check_page(self, url, *, label, expect_data_table=False):
        """Render ``url`` in both themes and run every coverage assertion."""
        for theme in THEME_COOKIES:
            with self.subTest(page=label, theme=theme or 'light'):
                if theme is None:
                    self.client.cookies.pop('theme', None)
                else:
                    self.client.cookies['theme'] = theme

                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, 200,
                    msg=f'[{label}, theme={theme or "light"}] expected HTTP '
                        f'200, got {response.status_code}.',
                )
                html = response.content.decode()

                self._assert_themed_base(html, label=label, theme=theme)
                self._assert_no_removed_bootstrap(html, label=label, theme=theme)

                if expect_data_table:
                    self.assertIn(
                        'data-table', html,
                        msg=f'[{label}, theme={theme or "light"}] dashboard '
                            f'page does not use the density component set '
                            f'(.data-table) required by Requirement 5.4.',
                    )


class PublicPagesCoverageSmokeTests(CoverageSmokeTestBase):
    """Every public reading/auth page, rendered as an anonymous Visitor.

    Validates: Requirements 2.1, 5.1, 5.3
    """

    def test_home_page(self):
        self._check_page(reverse('home'), label='home')

    def test_article_detail_page(self):
        self._check_page(
            reverse('Blog_detail', args=[self.post.slug]),
            label='article detail',
        )

    def test_category_archive_page(self):
        self._check_page(
            reverse('posts_by_category', args=[self.category.id]),
            label='category archive',
        )

    def test_category_index_page(self):
        self._check_page(reverse('category_index'), label='category index')

    def test_search_page(self):
        self._check_page(
            f"{reverse('search')}?keyword=probe", label='search results',
        )

    def test_author_profile_public_page(self):
        # Anonymous Visitor -> spacious public presentation (Requirement 5.5).
        self._check_page(
            reverse('author_profile', args=[self.author.username]),
            label='author profile (public)',
        )

    def test_login_page(self):
        self._check_page(reverse('login'), label='login')

    def test_register_page(self):
        self._check_page(reverse('register'), label='register')

    def test_password_reset_page(self):
        self._check_page(reverse('password_reset'), label='password reset')


class ReaderPagesCoverageSmokeTests(CoverageSmokeTestBase):
    """Pages that require an authenticated (non-editor) Reader.

    Validates: Requirements 2.1, 5.1, 5.3
    """

    def setUp(self):
        self.client.force_login(self.reader)

    def test_following_feed_page(self):
        # The reader follows the author, so the feed renders a populated grid.
        self._check_page(reverse('following_feed'), label='following feed')


class EditorPagesCoverageSmokeTests(CoverageSmokeTestBase):
    """Author profile density branch + every dashboard page, as an Editor.

    Validates: Requirements 2.1, 5.1, 5.3, 5.4
    """

    def setUp(self):
        self.client.force_login(self.editor)

    def test_author_profile_density_page(self):
        # Editor viewer -> density-optimized presentation with .data-table
        # (Requirement 5.6 + 5.4).
        self._check_page(
            reverse('author_profile', args=[self.author.username]),
            label='author profile (editor density)',
            expect_data_table=True,
        )

    def test_dashboard_home_page(self):
        self._check_page(
            reverse('dashboard'), label='dashboard home', expect_data_table=True
        )

    def test_dashboard_posts_page(self):
        self._check_page(
            reverse('posts'), label='dashboard posts', expect_data_table=True
        )

    def test_dashboard_categories_page(self):
        self._check_page(
            reverse('categories'), label='dashboard categories',
            expect_data_table=True,
        )

    def test_dashboard_comments_page(self):
        self._check_page(
            reverse('dashboard_comments'), label='dashboard comments',
            expect_data_table=True,
        )

    def test_dashboard_users_page(self):
        self._check_page(
            reverse('users'), label='dashboard users', expect_data_table=True
        )

    def test_dashboard_messages_page(self):
        self._check_page(
            reverse('contact_messages'), label='dashboard messages',
            expect_data_table=True,
        )
