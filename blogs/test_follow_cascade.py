"""Property-based tests for cascade deletion of Follow edges.

# Feature: editorial-revamp, Property 7: Deleting a User removes all Follow edges touching them

Property 7 states: for any follow graph, after deleting a User, no Follow
record remains that references that User as either follower or followed. This
is guaranteed by ``on_delete=CASCADE`` on both the ``follower`` and
``followed`` foreign keys of the Follow model.

Validates: Requirements 6.4
"""

from django.contrib.auth.models import User
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# A small pool of distinct users to build a follow graph from. Using a fixed
# pool created once keeps the generated space meaningful (real distinct User
# pairs) while every Follow row is rolled back between examples.
POOL_SIZE = 5

# Candidate directed edges: every ordered (follower, followed) pair of distinct
# indices within the pool. Self-pairs are excluded because the model forbids
# self-follows (prevent_self_follow CheckConstraint).
ALL_EDGES = [
    (i, j)
    for i in range(POOL_SIZE)
    for j in range(POOL_SIZE)
    if i != j
]

# A follow graph is any subset of the candidate edges.
follow_graphs = st.lists(
    st.sampled_from(ALL_EDGES),
    unique=True,
    max_size=len(ALL_EDGES),
)

# The index of the User to delete.
victim_index = st.integers(min_value=0, max_value=POOL_SIZE - 1)


class FollowCascadeDeletionProperty(TestCase):
    @settings(max_examples=25, deadline=None)
    @given(edges=follow_graphs, victim=victim_index)
    def test_deleting_user_removes_all_touching_follow_edges(self, edges, victim):
        # Feature: editorial-revamp, Property 7: Deleting a User removes all
        # Follow edges touching them (Validates: Requirements 6.4)

        # Users are created fresh for each example. Deleting a User mutates the
        # in-memory instance (its pk is cleared), so a per-class fixture would
        # be corrupted once the first example deletes its victim; building the
        # pool inside the test keeps every example independent.
        users = [
            User.objects.create_user(
                username=f'cascade-user-{i}', password='test-password'
            )
            for i in range(POOL_SIZE)
        ]

        # Build the follow graph.
        for follower_idx, followed_idx in edges:
            Follow.objects.create(
                follower=users[follower_idx],
                followed=users[followed_idx],
            )

        victim_user = users[victim]
        victim_id = victim_user.pk

        # Edges that reference the victim as either follower or followed are the
        # ones expected to disappear; edges touching neither must survive.
        expected_surviving = {
            (f, t)
            for (f, t) in edges
            if f != victim and t != victim
        }

        # Deleting the User must cascade to every Follow row touching them.
        victim_user.delete()

        # No Follow record references the deleted User as follower...
        self.assertFalse(
            Follow.objects.filter(follower_id=victim_id).exists(),
            msg='a Follow record still references the deleted User as follower',
        )
        # ...or as followed.
        self.assertFalse(
            Follow.objects.filter(followed_id=victim_id).exists(),
            msg='a Follow record still references the deleted User as followed',
        )

        # Every Follow edge not touching the deleted User is left intact.
        remaining = {
            (f.follower_id, f.followed_id) for f in Follow.objects.all()
        }
        expected_ids = {
            (users[f].pk, users[t].pk)
            for (f, t) in expected_surviving
        }
        self.assertEqual(
            remaining,
            expected_ids,
            msg=(
                'follow edges not touching the deleted User must remain '
                'unchanged after the cascade'
            ),
        )
