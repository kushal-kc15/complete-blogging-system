"""Property-based tests for follow uniqueness and idempotency.

# Feature: editorial-revamp, Property 5: Following is unique and idempotent

Property 5 states: for any pair of distinct Users (follower, followed),
performing the follow action one or more times results in exactly one Follow
record for that pair. The follow action is modeled at the data layer via
``get_or_create``, backed by the ``unique_follow`` UniqueConstraint on the
Follow model.

Validates: Requirements 6.2, 7.3
"""

from django.contrib.auth.models import User
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# A small pool of distinct users to draw follower/followed pairs from. Using a
# fixed pool created once keeps the generated space meaningful (real distinct
# User pairs) while every Follow row is rolled back between examples.
POOL_SIZE = 4

# Number of times the follow action is repeated for a given pair. Always >= 1 so
# the "one or more times" clause of the property is exercised.
repeat_counts = st.integers(min_value=1, max_value=6)


class FollowUniqueIdempotentProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User.objects.create_user(
                username=f'follow-user-{i}', password='test-password'
            )
            for i in range(POOL_SIZE)
        ]

    @settings(max_examples=25, deadline=None)
    @given(
        pair=st.lists(
            st.integers(min_value=0, max_value=POOL_SIZE - 1),
            min_size=2, max_size=2, unique=True,
        ),
        times=repeat_counts,
    )
    def test_following_is_unique_and_idempotent(self, pair, times):
        # Feature: editorial-revamp, Property 5: Following is unique and
        # idempotent (Validates: Requirements 6.2, 7.3)
        follower = self.users[pair[0]]
        followed = self.users[pair[1]]

        created_flags = []
        for _ in range(times):
            _, created = Follow.objects.get_or_create(
                follower=follower, followed=followed
            )
            created_flags.append(created)

        # Exactly one Follow record exists for the distinct pair, no matter how
        # many times the follow action was performed.
        self.assertEqual(
            Follow.objects.filter(
                follower=follower, followed=followed
            ).count(),
            1,
            msg=(
                f'following ({follower.username} -> {followed.username}) '
                f'{times} time(s) must yield exactly one Follow record'
            ),
        )

        # Idempotency: only the first action creates a row; every subsequent
        # action is a no-op that returns the existing record.
        self.assertTrue(
            created_flags[0],
            msg='the first follow action must create the record',
        )
        self.assertTrue(
            all(not c for c in created_flags[1:]),
            msg='repeat follow actions must not create additional records',
        )
