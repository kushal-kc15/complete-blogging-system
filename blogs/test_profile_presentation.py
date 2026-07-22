"""Property-based test for permission-based author-profile presentation.

# Feature: editorial-revamp, Property 4: Author-profile presentation is selected by Editor permission

Property 4 states: for any viewer of an Author Profile Page, the page renders
using the density-optimized Dashboard presentation *if and only if* the viewer
holds Editor permission (staff OR ``blogs.change_blog``); every viewer without
Editor permission (including Visitors / anonymous and non-Editor Readers)
receives the spacious public presentation.

Validates: Requirements 5.5, 5.6
"""

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# The five viewer positions in the permission matrix. Each tuple is
# (kind, expected_density). Density is expected iff the viewer is an Editor
# (staff OR holds blogs.change_blog); every non-Editor gets the spacious
# presentation, including anonymous Visitors and the author viewing self.
VIEWER_KINDS = [
    ('anonymous', False),      # Visitor -> spacious (Req 5.5)
    ('reader', False),         # authenticated, no perms -> spacious (Req 5.5)
    ('staff', True),           # Editor via is_staff -> density (Req 5.6)
    ('change_blog', True),     # Editor via blogs.change_blog -> density (Req 5.6)
    ('author_self', False),    # non-Editor author viewing own page -> spacious
]

viewer_kind = st.sampled_from(VIEWER_KINDS)


class ProfilePresentationPermissionProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Presentation Category')
        # The author whose profile is rendered. A plain (non-Editor) user so
        # the "author_self" viewer is a non-Editor and must see spacious.
        cls.author = User.objects.create_user(
            username='profile-author', password='pw'
        )
        # A published post guarantees the density branch renders its
        # ``.data-table`` and the spacious branch renders its
        # ``.post-grid--asymmetric`` grid, giving stable branch markers.
        Blog.objects.create(
            title='Presentation probe',
            slug='presentation-probe',
            category=cls.category,
            author=cls.author,
            short_description='probe',
            blog_body='<p>probe</p>',
            status='published',
        )
        cls.change_blog_perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Blog),
            codename='change_blog',
        )
        cls.url = reverse('author_profile', args=[cls.author.username])

    def _make_viewer(self, kind):
        """Return the User to log in as (or None for anonymous)."""
        if kind == 'anonymous':
            return None
        if kind == 'author_self':
            return self.author
        viewer = User.objects.create_user(username='viewer', password='pw')
        if kind == 'staff':
            viewer.is_staff = True
            viewer.save(update_fields=['is_staff'])
        elif kind == 'change_blog':
            viewer.user_permissions.add(self.change_blog_perm)
        return viewer

    @settings(max_examples=25, deadline=None)
    @given(kind_expected=viewer_kind)
    def test_density_presentation_iff_editor_permission(self, kind_expected):
        # Feature: editorial-revamp, Property 4: Author-profile presentation is
        # selected by Editor permission (Validates: Requirements 5.5, 5.6)
        kind, expected_density = kind_expected

        viewer = self._make_viewer(kind)
        if viewer is not None:
            self.client.force_login(viewer)
        else:
            self.client.logout()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        # Task-specified distinguishing markers. The DENSITY branch renders a
        # compact ``.data-table`` listing; the SPACIOUS branch renders the
        # ``author-header`` hero and a ``.post-grid--asymmetric`` grid. A
        # published post exists for the author, so the listing markers render
        # in whichever branch is selected. These markers are branch-exclusive
        # (unlike the shared layout ``container-*`` classes in base.html).
        has_data_table = 'data-table' in html
        has_post_grid = 'post-grid--asymmetric' in html
        has_author_header = 'author-header' in html

        detail = (
            f'kind={kind!r} expected_density={expected_density} '
            f'data_table={has_data_table} post_grid={has_post_grid} '
            f'author_header={has_author_header}'
        )

        if expected_density:
            # Editor -> density presentation only.
            self.assertTrue(has_data_table, detail)
            self.assertFalse(has_post_grid, detail)
            self.assertFalse(has_author_header, detail)
        else:
            # Non-Editor (incl. Visitor / anonymous) -> spacious presentation.
            self.assertTrue(has_author_header, detail)
            self.assertTrue(has_post_grid, detail)
            self.assertFalse(has_data_table, detail)
