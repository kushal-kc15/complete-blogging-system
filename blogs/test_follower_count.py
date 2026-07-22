"""Property-based tests for follower-count accuracy on the author profile.

# Feature: editorial-revamp, Property 13: Follower count matches Follow records

Property 13 states: for any follow graph, the follower count displayed for an
Author equals the number of Follow records in which that Author is the followed
User.

The property is exercised end-to-end. ``AuthorProfile`` computes
``follower_count = Follow.objects.filter(followed=author).count()`` and
``author_profile.html`` renders it as
``{{ follower_count }} follower{{ follower_count|pluralize }}``. Each example
generates a random number of distinct followers for the author, renders the
profile page, and asserts the rendered count string equals the actual number of
Follow records where the author is the followed User.

Validates: Requirements 9.1
"""

from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# Number of followers to generate for the author. Bounded to keep each example
# cheap while still exercising the empty case (0), the singular case (1, which
# also exercises Django's ``pluralize`` boundary), and many-follower cases.
follower_counts = st.integers(min_value=0, max_value=12)


class FollowerCountAccuracyProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='count-author', password='test-password'
        )
        cls.url = reverse('author_profile', args=[cls.author.username])

    @settings(max_examples=25, deadline=None)
    @given(num_followers=follower_counts)
    def test_displayed_follower_count_matches_follow_records(self, num_followers):
        # Feature: editorial-revamp, Property 13: Follower count matches Follow
        # records (Validates: Requirements 9.1)

        # Create ``num_followers`` distinct users, each following the author.
        # Each example runs in a rolled-back transaction, so state is fresh.
        for i in range(num_followers):
            follower = User.objects.create_user(
                username=f'follower-{i}', password='test-password'
            )
            Follow.objects.create(follower=follower, followed=self.author)

        # The actual number of Follow records where the author is followed --
        # the oracle the display must match (Requirement 9.1).
        actual_count = Follow.objects.filter(followed=self.author).count()
        self.assertEqual(
            actual_count,
            num_followers,
            msg='precondition: created Follow records must match generated count',
        )

        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code, 200,
            msg='author profile page should render',
        )
        content = response.content.decode('utf-8')

        # Django's ``pluralize`` yields '' for 1 and 's' otherwise, so the
        # rendered text is "<n> follower" (n == 1) or "<n> followers".
        suffix = '' if actual_count == 1 else 's'
        expected = f'{actual_count} follower{suffix}'

        self.assertIn(
            expected,
            content,
            msg=(
                f'displayed follower count must equal the {actual_count} Follow '
                f'record(s); expected the string {expected!r} in the response'
            ),
        )

        # Guard against an off-by-one/stale display: the count for a different
        # number of followers must not appear with the "follower" label.
        for wrong in (actual_count - 1, actual_count + 1):
            if wrong < 0:
                continue
            wrong_suffix = '' if wrong == 1 else 's'
            wrong_text = f'{wrong} follower{wrong_suffix}'
            # Skip if the wrong string is a substring of the expected string
            # (cannot happen here since counts differ), otherwise assert absent.
            self.assertNotIn(
                wrong_text,
                content,
                msg=(
                    f'a follower count of {actual_count} must not render the '
                    f'string {wrong_text!r}'
                ),
            )
