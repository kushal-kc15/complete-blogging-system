"""Property-based tests for permission-gated preview access.

# Feature: editorial-revamp, Property 16: Preview access to non-public posts
# is permission-gated.

Property 16 states: for any non-public post (a draft, or a Scheduled_Blog whose
Publication_Time has not passed) and any requester, the article detail page is
viewable if and only if the requester is the post's author, is staff, or holds
``blogs.change_blog``; every other requester (including Visitors) receives a 404
as if the post does not exist.

Validates: Requirements 11.5, 11.6, 13.3
"""

import datetime as dt

from django.contrib.auth.models import Permission, User
from django.urls import reverse
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


# A fixed, timezone-aware reference "now". Scheduled posts are dated after this
# instant so they are genuinely not-yet-due at evaluation time.
REFERENCE = dt.datetime(2024, 6, 15, 12, 0, 0, tzinfo=dt.timezone.utc)

# The viewer permission matrix. Only author/staff/perm are authorized to
# preview a non-public post; anonymous and a plain reader are not.
AUTHORIZED_ROLES = frozenset({'author', 'staff', 'perm'})


class Property16PreviewAccessTests(TestCase):
    """Property 16: Preview access to non-public posts is permission-gated.

    Validates: Requirements 11.5, 11.6, 13.3
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Preview Access')

        # The author of the non-public post under test.
        cls.author = User.objects.create_user(
            username='preview-author', password='test-password'
        )
        # A plain authenticated reader with no elevated permissions.
        cls.reader = User.objects.create_user(
            username='preview-reader', password='test-password'
        )
        # A staff user (is_staff grants preview via the existing rule).
        cls.staff = User.objects.create_user(
            username='preview-staff', password='test-password', is_staff=True
        )
        # A non-staff user holding the blogs.change_blog permission.
        cls.perm_user = User.objects.create_user(
            username='preview-perm', password='test-password'
        )
        cls.perm_user.user_permissions.add(
            Permission.objects.get(
                codename='change_blog', content_type__app_label='blogs'
            )
        )

    def _make_non_public_blog(self, *, kind):
        """Create a non-public Blog: either a draft or a not-yet-due scheduled post."""
        if kind == 'draft':
            status = 'draft'
            published_at = None
        else:  # 'scheduled'
            status = 'published'
            # Comfortably in the future relative to REFERENCE so it is not due.
            published_at = REFERENCE + dt.timedelta(days=7)

        return Blog.objects.create(
            title='Hidden candidate',
            slug='hidden-candidate',
            category=self.category,
            author=self.author,
            short_description='A non-public candidate post.',
            blog_body='<p>Body</p>',
            status=status,
            published_at=published_at,
        )

    def _viewer_for_role(self, role):
        return {
            'anonymous': None,
            'reader': self.reader,
            'author': self.author,
            'staff': self.staff,
            'perm': self.perm_user,
        }[role]

    @settings(max_examples=25, deadline=None)
    @given(
        role=st.sampled_from(
            ['anonymous', 'reader', 'author', 'staff', 'perm']
        ),
        kind=st.sampled_from(['draft', 'scheduled']),
    )
    def test_preview_access_is_permission_gated(self, role, kind):
        # Feature: editorial-revamp, Property 16: Preview access to non-public
        # posts is permission-gated (Validates: Requirements 11.5, 11.6, 13.3)
        with freeze_time(REFERENCE):
            post = self._make_non_public_blog(kind=kind)

            # Fresh client per example so authentication state does not leak.
            self.client.logout()
            viewer = self._viewer_for_role(role)
            if viewer is not None:
                self.client.force_login(viewer)

            url = reverse('Blog_detail', kwargs={'slug': post.slug})
            response = self.client.get(url)

        expected_viewable = role in AUTHORIZED_ROLES
        if expected_viewable:
            self.assertEqual(
                response.status_code,
                200,
                msg=(
                    f'role={role!r} kind={kind!r}: authorized previewer should '
                    f'see the post (200), got {response.status_code}'
                ),
            )
        else:
            self.assertEqual(
                response.status_code,
                404,
                msg=(
                    f'role={role!r} kind={kind!r}: unauthorized requester must '
                    f'receive 404, got {response.status_code}'
                ),
            )
