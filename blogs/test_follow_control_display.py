"""Property-based tests for the displayed follow/unfollow control.

# Feature: editorial-revamp, Property 8: Displayed control reflects follow state

Property 8 states: for any authenticated viewer looking at another User's
Author Profile Page, the page displays the unfollow control when a Follow
record from viewer to author exists, and the follow control when it does not.

The property is exercised end-to-end by rendering the ``author_profile`` view
as an authenticated viewer on another user's profile. ``author_profile.html``
renders a POST form to ``follow_author`` when the viewer is not following and a
POST form to ``unfollow_author`` when the viewer is following, so the two
controls are distinguished by their form ``action`` URL.

Validates: Requirements 7.1, 7.2
"""

from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# A small pool of distinct users to draw (viewer, author) pairs from. The pool
# is created once; any Follow row created by an example is rolled back between
# examples by the Hypothesis/Django transactional TestCase.
POOL_SIZE = 4

# Candidate directed (viewer, author) pairs of distinct pool indices. The
# property concerns a viewer looking at *another* user's profile, so self-pairs
# (own profile) are excluded here.
DISTINCT_PAIRS = [
    (i, j)
    for i in range(POOL_SIZE)
    for j in range(POOL_SIZE)
    if i != j
]


class FollowControlDisplayProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User.objects.create_user(
                username=f'control-user-{i}', password='test-password'
            )
            for i in range(POOL_SIZE)
        ]

    @settings(max_examples=25, deadline=None)
    @given(
        pair=st.sampled_from(DISTINCT_PAIRS),
        record_exists=st.booleans(),
    )
    def test_displayed_control_reflects_follow_state(self, pair, record_exists):
        # Feature: editorial-revamp, Property 8: Displayed control reflects
        # follow state (Validates: Requirements 7.1, 7.2)
        viewer = self.users[pair[0]]
        author = self.users[pair[1]]

        # Toggle whether a Follow record exists for this (viewer -> author)
        # pair. Each example runs in a rolled-back transaction, so the state is
        # established fresh per example.
        if record_exists:
            Follow.objects.create(follower=viewer, followed=author)

        # Sanity-check the precondition matches the toggle so a leak surfaces
        # as a failed precondition rather than a false pass.
        self.assertEqual(
            Follow.objects.filter(follower=viewer, followed=author).exists(),
            record_exists,
            msg='precondition: Follow record existence must match the toggle',
        )

        self.client.force_login(viewer)
        response = self.client.get(
            reverse('author_profile', args=[author.username])
        )
        self.assertEqual(
            response.status_code, 200,
            msg='author profile page should render for an authenticated viewer',
        )
        content = response.content.decode('utf-8')

        # The two controls are distinguished by their form action URL. Note
        # that the follow URL (".../follow/") is not a substring of the
        # unfollow URL (".../unfollow/"), so the two markers are unambiguous.
        follow_action = 'action="%s"' % reverse(
            'follow_author', args=[author.username]
        )
        unfollow_action = 'action="%s"' % reverse(
            'unfollow_author', args=[author.username]
        )

        if record_exists:
            # A Follow record exists -> the unfollow control is shown and the
            # follow control is not (Requirement 7.2).
            self.assertIn(
                unfollow_action, content,
                msg=(
                    f'{viewer.username} follows {author.username}: the '
                    f'unfollow control must be displayed'
                ),
            )
            self.assertNotIn(
                follow_action, content,
                msg=(
                    f'{viewer.username} follows {author.username}: the follow '
                    f'control must not be displayed'
                ),
            )
        else:
            # No Follow record -> the follow control is shown and the unfollow
            # control is not (Requirement 7.1).
            self.assertIn(
                follow_action, content,
                msg=(
                    f'{viewer.username} does not follow {author.username}: the '
                    f'follow control must be displayed'
                ),
            )
            self.assertNotIn(
                unfollow_action, content,
                msg=(
                    f'{viewer.username} does not follow {author.username}: the '
                    f'unfollow control must not be displayed'
                ),
            )
