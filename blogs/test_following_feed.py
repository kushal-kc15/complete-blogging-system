"""Property-based tests for the Following Feed contents.

# Feature: editorial-revamp, Property 12: Following Feed contains exactly published-due posts by followed authors

Property 12 states: for any set of Users, follow relationships, and posts, the
Following Feed for a given Reader contains exactly those posts that are
Published_Blog posts (status ``published`` and Publication_Time at or before
now) authored by Users the Reader follows, ordered most-recently-published
first -- and contains no post authored by a non-followed User and no
unpublished or not-yet-due Scheduled_Blog post.

The test builds a graph of authors (some followed, some not) and posts across
every relevant state (draft, future-dated Scheduled_Blog, and published-due),
exercises the real ``following_feed`` view through the logged-in test client,
and compares the view's full ordered queryset against a plain-Python model
oracle. ``now`` is frozen so the read-time scheduling comparison is
deterministic.

Validates: Requirements 8.1, 8.2, 11.4
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from django.urls import reverse
from freezegun import freeze_time
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase

from .models import Blog, Category, Follow


# A fixed, tz-aware reference instant. Matching the project's USE_TZ / UTC setup
# keeps the read-time ``published_at <= now`` comparison unambiguous. Every
# post's Publication_Time is expressed as an offset from BASE, and the feed is
# evaluated with ``now`` frozen at BASE.
BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)


@st.composite
def follow_graphs(draw):
    """Generate authors (each flagged followed/not) and posts across states.

    Each post carries an author index, a status (draft/published) and a
    ``due`` flag. The concrete Publication_Time is derived per post from its
    position so that every post gets a unique ``published_at`` -- this makes
    the newest-first ordering total and therefore deterministically checkable.
    """
    n_authors = draw(st.integers(min_value=1, max_value=4))
    followed_flags = draw(
        st.lists(st.booleans(), min_size=n_authors, max_size=n_authors)
    )
    posts = draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    'author_idx': st.integers(min_value=0, max_value=n_authors - 1),
                    'status': st.sampled_from(['draft', 'published']),
                    # For published posts, ``due`` selects a past Publication_Time
                    # (a Published_Blog) vs a future one (a Scheduled_Blog).
                    'due': st.booleans(),
                }
            ),
            min_size=0,
            max_size=8,
        )
    )
    return followed_flags, posts


class FollowingFeedContentsProperty(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Feed Category')
        cls.reader = User.objects.create_user(
            username='feed-reader', password='reader-password'
        )

    def _publication_time(self, index, status, due):
        """Derive a unique Publication_Time for the post at ``index``.

        Published + due  -> a past instant (a Published_Blog, in the feed).
        Published + !due -> a future instant (a Scheduled_Blog, excluded).
        Draft            -> a past instant, to prove the status gate excludes
                            it even though its time has passed.
        Offsets are unique per index (negatives for past, positives for
        future, never overlapping), so no two feed rows share a published_at.
        """
        magnitude = index + 1
        if status == 'published' and not due:
            return BASE + timedelta(seconds=magnitude)
        return BASE - timedelta(seconds=magnitude)

    def _make_blog(self, index, author, status, published_at):
        """Create a Blog with an exact status/published_at.

        ``Blog.save()`` auto-stamps ``published_at`` on publish, so the exact
        value is written via ``update()`` (bypassing ``save()``) to reproduce
        every state the property covers.
        """
        blog = Blog.objects.create(
            title=f'Feed probe {index}',
            slug=f'feed-probe-{index}',
            category=self.category,
            author=author,
            short_description='probe',
            blog_body='<p>probe</p>',
            status='draft',
        )
        Blog.objects.filter(pk=blog.pk).update(
            status=status, published_at=published_at
        )
        return blog.pk

    @settings(max_examples=25, deadline=None)
    @given(graph=follow_graphs())
    def test_following_feed_matches_oracle(self, graph):
        # Feature: editorial-revamp, Property 12: Following Feed contains
        # exactly published-due posts by followed authors
        # (Validates: Requirements 8.1, 8.2, 11.4)
        followed_flags, post_specs = graph

        with freeze_time(BASE):
            # Build the author graph; follow only the flagged authors.
            authors = []
            for i, followed in enumerate(followed_flags):
                author = User.objects.create_user(
                    username=f'feed-author-{i}', password='author-password'
                )
                authors.append(author)
                if followed:
                    Follow.objects.create(follower=self.reader, followed=author)

            # Materialize the posts and, in parallel, compute the oracle:
            # feed-eligible == status published AND due (published_at <= now)
            # AND authored by a followed User.
            oracle_entries = []  # (published_at, pk) for eligible posts
            for index, spec in enumerate(post_specs):
                author = authors[spec['author_idx']]
                status = spec['status']
                due = spec['due']
                published_at = self._publication_time(index, status, due)
                pk = self._make_blog(index, author, status, published_at)

                is_published_due = status == 'published' and due
                is_followed = followed_flags[spec['author_idx']]
                if is_published_due and is_followed:
                    oracle_entries.append((published_at, pk))

            # Oracle order: most-recently-published first. Publication_Times are
            # unique per post, so ordering is total and deterministic.
            oracle_entries.sort(key=lambda entry: entry[0], reverse=True)
            expected_order = [pk for _, pk in oracle_entries]
            expected_set = set(expected_order)

            # Exercise the real view as the logged-in Reader.
            self.client.force_login(self.reader)
            response = self.client.get(reverse('following_feed'))
            self.assertEqual(response.status_code, 200)

            # ``posts`` is a paginated Page; its paginator's object_list is the
            # full ordered feed queryset (independent of the current page).
            page = response.context['posts']
            actual_order = list(
                page.paginator.object_list.values_list('pk', flat=True)
            )

        actual_set = set(actual_order)

        # Membership: exactly the published-due posts by followed authors.
        self.assertEqual(
            actual_set,
            expected_set,
            msg=(
                'Following feed membership mismatch.\n'
                f'unexpected (in feed, not oracle): {actual_set - expected_set}\n'
                f'missing (in oracle, not feed): {expected_set - actual_set}'
            ),
        )
        # Order: newest published first.
        self.assertEqual(
            actual_order,
            expected_order,
            msg=(
                'Following feed ordering mismatch.\n'
                f'actual:   {actual_order}\n'
                f'expected: {expected_order}'
            ),
        )
