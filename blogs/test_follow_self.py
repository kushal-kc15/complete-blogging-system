"""Property-based tests for self-follow rejection.

# Feature: editorial-revamp, Property 6: Self-follow is rejected

Property 6 states: for any User, attempting to follow themselves creates no
Follow record and the attempt is rejected. Rejection is enforced at two
independent layers:

* the model ``clean()`` guard (friendly application-level rejection via
  ``ValidationError``), and
* the database ``CheckConstraint`` named ``prevent_self_follow`` (the backstop
  that rejects a self-follow row with an ``IntegrityError`` even if ``clean()``
  is bypassed).

Either way, no Follow record for the (user, user) pair is ever persisted.

Validates: Requirements 6.3
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Follow


# A small pool of distinct users to draw the self-follow subject from. Created
# once; every Follow row attempted below is rolled back between examples.
POOL_SIZE = 4


class SelfFollowRejectedProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User.objects.create_user(
                username=f'self-follow-user-{i}', password='test-password'
            )
            for i in range(POOL_SIZE)
        ]

    @settings(max_examples=25, deadline=None)
    @given(index=st.integers(min_value=0, max_value=POOL_SIZE - 1))
    def test_self_follow_is_rejected(self, index):
        # Feature: editorial-revamp, Property 6: Self-follow is rejected
        # (Validates: Requirements 6.3)
        user = self.users[index]

        before = Follow.objects.filter(follower=user, followed=user).count()
        self.assertEqual(
            before, 0, msg='precondition: no self-follow row should exist'
        )

        # Layer 1: the model clean() guard rejects the self-follow attempt with
        # a friendly ValidationError before any row is written.
        with self.assertRaises(ValidationError):
            Follow(follower=user, followed=user).clean()

        # Layer 2: the DB CheckConstraint `prevent_self_follow` rejects the row
        # even when clean() is bypassed (a direct save). The write is wrapped in
        # an atomic block so the broken transaction is contained and rolled back.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Follow.objects.create(follower=user, followed=user)

        # Neither layer created a self-follow record.
        self.assertEqual(
            Follow.objects.filter(follower=user, followed=user).count(),
            0,
            msg=(
                f'attempting to self-follow ({user.username}) must not create '
                f'any Follow record'
            ),
        )
