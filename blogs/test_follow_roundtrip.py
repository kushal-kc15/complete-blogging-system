"""Property-based tests for follow/unfollow round-trip.

# Feature: editorial-revamp, Property 9: Follow then unfollow round-trips to the original state

Property 9 states: for any authenticated viewer and distinct author,
performing a follow action followed by an unfollow action leaves no Follow
record between them, returning the relationship to its original unfollowed
state.

The follow/unfollow actions are exercised through the wired views
(``follow_author`` / ``unfollow_author``, POST-only, ``@login_required``) so
the round-trip is validated end-to-end through the same path a Reader uses,
rather than at the model layer only.

Validates: Requirements 7.4
"""

from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# A small pool of distinct users to draw (follower, followed) pairs from. The
# pool is created once; every Follow row created by an example is rolled back
# between examples by the Hypothesis/Django transactional TestCase.
POOL_SIZE = 4

# Candidate directed edges: every ordered (follower, followed) pair of distinct
# indices within the pool. Self-pairs are excluded because the property is
# about a viewer and a *distinct* author (self-follow is a separate property).
DISTINCT_PAIRS = [
    (i, j)
    for i in range(POOL_SIZE)
    for j in range(POOL_SIZE)
    if i != j
]


class FollowUnfollowRoundTripProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User.objects.create_user(
                username=f'roundtrip-user-{i}', password='test-password'
            )
            for i in range(POOL_SIZE)
        ]

    @settings(max_examples=25, deadline=None)
    @given(pair=st.sampled_from(DISTINCT_PAIRS))
    def test_follow_then_unfollow_round_trips_to_unfollowed(self, pair):
        # Feature: editorial-revamp, Property 9: Follow then unfollow
        # round-trips to the original state (Validates: Requirements 7.4)
        follower = self.users[pair[0]]
        followed = self.users[pair[1]]

        # Precondition: the relationship starts unfollowed. Guaranteed because
        # each example runs in a rolled-back transaction, but asserted so a
        # leak would surface as a failed precondition rather than a false pass.
        self.assertEqual(
            Follow.objects.filter(
                follower=follower, followed=followed
            ).count(),
            0,
            msg='precondition: no Follow record should exist before the round-trip',
        )

        self.client.force_login(follower)

        # Follow via the wired POST view.
        follow_response = self.client.post(
            reverse('follow_author', args=[followed.username])
        )
        self.assertEqual(
            follow_response.status_code, 302,
            msg='follow POST should redirect back to the profile',
        )
        # The follow action must actually establish the relationship, otherwise
        # the round-trip would trivially "pass" without exercising anything.
        self.assertEqual(
            Follow.objects.filter(
                follower=follower, followed=followed
            ).count(),
            1,
            msg='follow action must create exactly one Follow record',
        )

        # Unfollow via the wired POST view.
        unfollow_response = self.client.post(
            reverse('unfollow_author', args=[followed.username])
        )
        self.assertEqual(
            unfollow_response.status_code, 302,
            msg='unfollow POST should redirect back to the profile',
        )

        # Round-trip invariant: no Follow record remains between the pair, so
        # the relationship is back in its original unfollowed state.
        self.assertEqual(
            Follow.objects.filter(
                follower=follower, followed=followed
            ).count(),
            0,
            msg=(
                f'follow-then-unfollow ({follower.username} -> '
                f'{followed.username}) must leave no Follow record'
            ),
        )
