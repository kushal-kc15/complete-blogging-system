"""Property-based tests for dashboard scheduling: past-time rejection.

Feature: editorial-revamp

These tests exercise the ``publication_time`` validation added to
``dashboard.forms.BlogForm`` in task 4.1. For a post that is not already
published, a Publication_Time in the past must be rejected with a message
requiring a future time, while any future Publication_Time must be accepted
(Requirement 12.3).
"""

import uuid
from datetime import timedelta

from django.utils import timezone
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from blogs.models import Category
from dashboard.forms import BlogForm, DATETIME_LOCAL_FORMAT

# The exact validation message emitted by BlogForm.clean for a past time on a
# not-yet-published post (see dashboard/forms.py).
FUTURE_MESSAGE = 'Publication Time must be in the future.'


def _make_category():
    """Create a Category with a unique name.

    ModelChoiceField validation queries the DB for the selected category, so
    the row must exist within the test's (rolled-back) transaction.
    """
    return Category.objects.create(name=f"Cat-{uuid.uuid4().hex[:12]}")


def _form_data(category, publication_time, status):
    """Build a full set of valid BlogForm field data.

    Only ``publication_time`` varies between examples; every other required
    field is populated with a valid value so that the form's validity is
    determined solely by the Publication_Time rule under test.
    """
    return {
        'title': 'A Scheduled Post',
        'category': category.pk,
        'featured_image_alt': '',
        'short_description': 'A short description for the post.',
        'blog_body': '<p>Body content.</p>',
        'status': status,
        'meta_description': '',
        # datetime-local widgets exchange values without seconds/timezone.
        'publication_time': publication_time.strftime(DATETIME_LOCAL_FORMAT),
    }


# Whole-minute offsets keep us clear of the second-level truncation the
# datetime-local format performs. A minimum of 2 minutes avoids any boundary
# flakiness as the wall clock advances during is_valid().
_minute_offset = st.integers(min_value=2, max_value=60 * 24 * 365)
_status = st.sampled_from(['draft', 'published'])


class PastPublicationTimeRejectedTest(HypothesisTestCase):
    """# Feature: editorial-revamp, Property 17: Past publication times are rejected before publish

    **Validates: Requirements 12.3**
    """

    @settings(max_examples=25, deadline=None)
    @given(minutes_ago=_minute_offset, status=_status)
    def test_past_time_is_rejected_with_future_message(self, minutes_ago, status):
        # For any Publication_Time in the past submitted for a Blog that is not
        # already published, the form is invalid and reports the future-time
        # message on the publication_time field.
        category = _make_category()
        past_time = timezone.localtime(timezone.now()) - timedelta(minutes=minutes_ago)

        form = BlogForm(data=_form_data(category, past_time, status))

        self.assertFalse(
            form.is_valid(),
            msg=f"Expected form to be invalid for a past time {minutes_ago} minutes ago",
        )
        self.assertIn('publication_time', form.errors)
        self.assertIn(FUTURE_MESSAGE, form.errors['publication_time'])

    @settings(max_examples=25, deadline=None)
    @given(minutes_ahead=_minute_offset, status=_status)
    def test_future_time_is_accepted(self, minutes_ahead, status):
        # For any Publication_Time in the future, the form accepts the value:
        # it is valid and carries no publication_time error.
        category = _make_category()
        future_time = timezone.localtime(timezone.now()) + timedelta(minutes=minutes_ahead)

        form = BlogForm(data=_form_data(category, future_time, status))

        self.assertTrue(
            form.is_valid(),
            msg=f"Expected form to be valid for a future time {minutes_ahead} "
                f"minutes ahead; errors: {form.errors.as_json()}",
        )
        self.assertNotIn('publication_time', form.errors)
