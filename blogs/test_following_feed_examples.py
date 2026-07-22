"""Deterministic example tests for the Following Feed redirect and empty state.

# Feature: editorial-revamp

These are example-based (NOT property-based) tests covering two acceptance
criteria of the Following Feed:

- Requirement 8.3: an unauthenticated Visitor requesting the Following_Feed is
  redirected to the login page (the view is ``@login_required``).
- Requirement 8.4: an authenticated Reader who follows no Users sees a named
  empty-state explaining that no followed authors have published posts yet,
  rather than an empty or broken listing.

The ``following_feed`` view renders ``following_feed.html``. When there are no
posts it renders a ``.empty-state`` block titled "Nothing here yet" with a
message about followed authors not having published anything.

Validates: Requirements 8.3, 8.4
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class FollowingFeedRedirectExampleTest(TestCase):
    """Requirement 8.3: anonymous access redirects to the login page."""

    def test_anonymous_get_redirects_to_login(self):
        # Validates: Requirements 8.3
        feed_url = reverse('following_feed')
        response = self.client.get(feed_url)

        # @login_required(login_url='login') sends the Visitor to the login
        # page with a ?next back to the feed rather than serving the feed.
        expected_url = f"{reverse('login')}?next={feed_url}"
        self.assertRedirects(
            response,
            expected_url,
            status_code=302,
            target_status_code=200,
            msg_prefix='anonymous request to following_feed must redirect to login',
        )


class FollowingFeedEmptyStateExampleTest(TestCase):
    """Requirement 8.4: a Reader following no one sees the named empty-state."""

    @classmethod
    def setUpTestData(cls):
        cls.reader = User.objects.create_user(
            username='lonely-reader', password='test-password'
        )

    def test_reader_following_no_one_sees_named_empty_state(self):
        # Validates: Requirements 8.4
        self.client.force_login(self.reader)
        response = self.client.get(reverse('following_feed'))

        # The Reader follows no one, so the feed renders the empty-state rather
        # than a listing or an error.
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'following_feed.html')

        # The empty-state is a named block: the .empty-state container, its
        # heading, and a message that explains no followed authors have
        # published posts yet.
        self.assertContains(response, 'empty-state')
        self.assertContains(response, 'Nothing here yet')
        self.assertContains(
            response,
            'None of the authors you follow have published posts yet.',
        )
