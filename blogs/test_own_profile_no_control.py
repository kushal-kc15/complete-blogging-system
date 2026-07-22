"""Property-based test for the absence of a follow control on one's own profile.

# Feature: editorial-revamp, Property 11: No follow control on one's own profile

Property 11 states: for any User viewing their own Author Profile Page, neither
a follow nor an unfollow control is present.

The property is exercised end-to-end by rendering the ``author_profile`` view
while logged in *as the profile owner*. ``author_profile.html`` only emits a
follow/unfollow control when ``show_follow_control`` is truthy, and the
``AuthorProfile`` view sets ``show_follow_control`` to
``request.user.is_authenticated and not is_self``. Viewing one's own profile
makes ``is_self`` true, so no control should appear -- in either the spacious
public presentation or the density-optimized Editor presentation.

To exercise the property across meaningfully different renders we vary whether
the owner is an Editor (via ``is_staff`` or ``blogs.change_blog``, which selects
the density vs spacious branch) and whether the owner has a published post
(which changes what the post listing renders). The absence of a control must
hold across all of these.

Validates: Requirements 7.6
"""

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category


class OwnProfileNoControlProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Own Profile Category')
        cls.change_blog_perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Blog),
            codename='change_blog',
        )

    @settings(max_examples=25, deadline=None)
    @given(
        is_staff=st.booleans(),
        has_change_blog=st.booleans(),
        has_post=st.booleans(),
    )
    def test_no_follow_control_on_own_profile(
        self, is_staff, has_change_blog, has_post
    ):
        # Feature: editorial-revamp, Property 11: No follow control on one's own
        # profile (Validates: Requirements 7.6)

        # Fresh owner per example; the transactional TestCase rolls back the
        # user, permission, and any post between examples.
        owner = User.objects.create_user(username='owner', password='pw')
        if is_staff:
            owner.is_staff = True
            owner.save(update_fields=['is_staff'])
        if has_change_blog:
            owner.user_permissions.add(self.change_blog_perm)

        if has_post:
            Blog.objects.create(
                title='Own probe',
                slug='own-probe',
                category=self.category,
                author=owner,
                short_description='probe',
                blog_body='<p>probe</p>',
                status='published',
            )

        # Log in AS the profile owner and request their own profile.
        self.client.force_login(owner)
        response = self.client.get(
            reverse('author_profile', args=[owner.username])
        )
        self.assertEqual(
            response.status_code, 200,
            msg='own author profile page should render for its owner',
        )
        content = response.content.decode('utf-8')

        # Both controls are rendered as POST forms whose action targets the
        # follow_author / unfollow_author routes for this username. Neither
        # form action may appear on the owner's own profile (Requirement 7.6).
        follow_action = 'action="%s"' % reverse(
            'follow_author', args=[owner.username]
        )
        unfollow_action = 'action="%s"' % reverse(
            'unfollow_author', args=[owner.username]
        )

        detail = (
            f'is_staff={is_staff} has_change_blog={has_change_blog} '
            f'has_post={has_post}'
        )
        self.assertNotIn(
            follow_action, content,
            msg=f'follow control must not appear on own profile ({detail})',
        )
        self.assertNotIn(
            unfollow_action, content,
            msg=f'unfollow control must not appear on own profile ({detail})',
        )
