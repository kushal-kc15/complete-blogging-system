"""Property-based test for anonymous follow/unfollow no-op redirect.

# Feature: editorial-revamp, Property 10: Anonymous follow/unfollow is a no-op redirect

Property 10 states: for any follow or unfollow submission made by an
unauthenticated Visitor, the response redirects to the login page and the set
of Follow records is unchanged.

The ``follow_author`` / ``unfollow_author`` views are POST-only and
``@login_required(login_url='login')``. Because ``@login_required`` intercepts
an unauthenticated request before the view body runs, the request never
mutates any Follow record and is redirected to the login page (with a ``next``
query parameter). This test drives the wired POST endpoints unauthenticated
across a randomly generated follow graph and asserts both halves of the
property: the redirect target is the login page, and the complete set of
Follow records is byte-for-byte identical before and after the request.

Validates: Requirements 7.5
"""

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# The login endpoint is wired at ``/login/`` under the name ``login`` and is the
# ``login_url`` on both follow views. @login_required redirects unauthenticated
# requests here with a ``?next=`` parameter.
LOGIN_PATH = reverse('login')


@st.composite
def follow_graphs(draw):
    """Generate a follow graph plus the anonymous action to attempt.

    Returns a tuple ``(num_users, edges, action, target_idx)`` where:
      * ``num_users`` users are created (usernames ``user0``..``userN-1``),
      * ``edges`` is a set of ``(follower_idx, followed_idx)`` pairs with
        ``follower != followed`` that seed the initial Follow records,
      * ``action`` is ``'follow'`` or ``'unfollow'`` (the endpoint attempted),
      * ``target_idx`` selects which user is the target of the action.
    """
    num_users = draw(st.integers(min_value=2, max_value=5))
    idx = st.integers(min_value=0, max_value=num_users - 1)
    pairs = st.tuples(idx, idx).filter(lambda p: p[0] != p[1])
    edges = draw(st.sets(pairs, max_size=num_users * (num_users - 1)))
    action = draw(st.sampled_from(['follow', 'unfollow']))
    target_idx = draw(idx)
    return num_users, edges, action, target_idx


class AnonymousFollowNoOpRedirectProperty(TestCase):
    def _snapshot(self):
        """Return the complete set of Follow edges as (follower, followed) ids."""
        return set(
            Follow.objects.values_list('follower_id', 'followed_id')
        )

    @settings(max_examples=25, deadline=None)
    @given(graph=follow_graphs())
    def test_anonymous_follow_unfollow_is_a_noop_redirect(self, graph):
        # Feature: editorial-revamp, Property 10: Anonymous follow/unfollow is a
        # no-op redirect (Validates: Requirements 7.5)
        num_users, edges, action, target_idx = graph

        users = [
            User.objects.create_user(
                username=f'user{i}', password='test-password'
            )
            for i in range(num_users)
        ]
        for follower_idx, followed_idx in edges:
            Follow.objects.create(
                follower=users[follower_idx], followed=users[followed_idx]
            )

        before = self._snapshot()
        target = users[target_idx]
        url = reverse(f'{action}_author', args=[target.username])

        # A fresh client with no authenticated session = an unauthenticated
        # Visitor submitting the control.
        anon = Client()
        response = anon.post(url)

        # The submission redirects to the login page rather than mutating data.
        self.assertEqual(
            response.status_code,
            302,
            msg=f'anonymous {action} POST should redirect, got {response.status_code}',
        )
        self.assertTrue(
            response.url.startswith(LOGIN_PATH),
            msg=(
                f'anonymous {action} POST should redirect to the login page '
                f'({LOGIN_PATH}); got {response.url!r}'
            ),
        )

        # The set of Follow records is completely unchanged (no create/delete).
        after = self._snapshot()
        self.assertEqual(
            after,
            before,
            msg=(
                f'anonymous {action} POST changed Follow records: '
                f'before={before} after={after}'
            ),
        )
