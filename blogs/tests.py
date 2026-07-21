from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.utils import timezone
from datetime import timedelta
from pathlib import Path

from .context_processors import GLOBAL_CATEGORIES_CACHE_KEY, get_categories
from .forms import BlogAdminForm, CommentForm
from .models import Blog, Bookmark, Category, Comment, Like, UserProfile
from .sanitizers import sanitize_rich_text
from blog_main.forms import UserProfileForm


class EngagementSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reader', password='test-password'
        )
        self.category = Category.objects.create(name='General')
        self.first_post = Blog.objects.create(
            title='First', slug='first', category=self.category,
            author=self.user, short_description='First post',
            blog_body='<p>First body</p>', status='published'
        )
        self.second_post = Blog.objects.create(
            title='Second', slug='second', category=self.category,
            author=self.user, short_description='Second post',
            blog_body='<p>Second body</p>', status='published'
        )
        self.parent = Comment.objects.create(
            user=self.user, blog=self.first_post, comment='Parent'
        )
        self.client.force_login(self.user)

    def test_like_and_bookmark_toggles_reject_get(self):
        self.assertEqual(
            self.client.get(reverse('like_post', args=[self.first_post.slug])).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(reverse('bookmark_post', args=[self.first_post.slug])).status_code,
            405,
        )
        self.assertFalse(Like.objects.exists())
        self.assertFalse(Bookmark.objects.exists())

    def test_delete_comment_rejects_get(self):
        response = self.client.get(reverse('delete_comment', args=[self.parent.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Comment.objects.filter(pk=self.parent.pk).exists())

    def test_comment_parent_must_belong_to_same_post(self):
        response = self.client.post(
            reverse('Blog_detail', args=[self.second_post.slug]),
            {'comment': 'Invalid reply', 'parent_id': self.parent.id},
            follow=True,
        )
        self.assertContains(response, 'The comment you tried to reply to is not valid.')
        self.assertFalse(Comment.objects.filter(comment='Invalid reply').exists())

    def test_invalid_comment_parent_is_handled(self):
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'Invalid reply', 'parent_id': 999999},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The comment you tried to reply to is not valid.')
        self.assertFalse(Comment.objects.filter(comment='Invalid reply').exists())

    def test_hidden_comments_do_not_appear_publicly(self):
        Comment.objects.create(
            user=self.user,
            blog=self.first_post,
            comment='Hidden moderation text',
            is_visible=False,
        )
        response = self.client.get(reverse('Blog_detail', args=[self.first_post.slug]))
        self.assertContains(response, 'Parent')
        self.assertNotContains(response, 'Hidden moderation text')

    def test_published_article_views_increment_atomically_and_refresh_display(self):
        response = self.client.get(
            reverse('Blog_detail', args=[self.first_post.slug])
        )
        self.first_post.refresh_from_db()
        self.assertEqual(self.first_post.views, 1)
        self.assertContains(response, '1 views')

        response = self.client.get(
            reverse('Blog_detail', args=[self.first_post.slug])
        )
        self.first_post.refresh_from_db()
        self.assertEqual(self.first_post.views, 2)
        self.assertContains(response, '2 views')

    def test_published_comment_post_preserves_view_increment_trigger(self):
        self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'A comment view'},
        )

        self.first_post.refresh_from_db()
        self.assertEqual(self.first_post.views, 1)

    def test_invalid_comment_post_preserves_view_increment_trigger(self):
        self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'Invalid parent view', 'parent_id': 'invalid'},
        )

        self.first_post.refresh_from_db()
        self.assertEqual(self.first_post.views, 1)

    def test_nonexistent_article_does_not_increment_existing_article(self):
        response = self.client.get('/article-that-does-not-exist-for-views/')

        self.assertEqual(response.status_code, 404)
        self.first_post.refresh_from_db()
        self.assertEqual(self.first_post.views, 0)

    def test_article_get_includes_unbound_comment_form(self):
        response = self.client.get(reverse('Blog_detail', args=[self.first_post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['comment_form'], CommentForm)
        self.assertFalse(response.context['comment_form'].is_bound)

    def test_authenticated_user_can_create_top_level_comment(self):
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'A validated top-level comment'},
        )

        self.assertRedirects(response, reverse('Blog_detail', args=[self.first_post.slug]))
        comment = Comment.objects.get(comment='A validated top-level comment')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.blog, self.first_post)
        self.assertIsNone(comment.parent)

    def test_authenticated_user_can_create_reply(self):
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'A validated reply', 'parent_id': self.parent.id},
        )

        self.assertRedirects(response, reverse('Blog_detail', args=[self.first_post.slug]))
        reply = Comment.objects.get(comment='A validated reply')
        self.assertEqual(reply.user, self.user)
        self.assertEqual(reply.blog, self.first_post)
        self.assertEqual(reply.parent, self.parent)

    def test_invalid_comment_content_is_rendered_with_errors(self):
        initial_count = Comment.objects.count()
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': '   '},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Comment.objects.count(), initial_count)

    def test_missing_comment_content_is_rejected(self):
        initial_count = Comment.objects.count()
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Comment.objects.count(), initial_count)

    def test_malformed_comment_parent_is_rejected_without_server_error(self):
        initial_count = Comment.objects.count()
        response = self.client.post(
            reverse('Blog_detail', args=[self.first_post.slug]),
            {'comment': 'Preserved comment text', 'parent_id': 'not-an-id'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The comment you tried to reply to is not valid.')
        self.assertContains(response, 'Preserved comment text')
        self.assertEqual(Comment.objects.count(), initial_count)

    def test_anonymous_comment_submission_redirects_to_login(self):
        self.client.logout()
        detail_url = reverse('Blog_detail', args=[self.first_post.slug])
        response = self.client.post(detail_url, {'comment': 'Anonymous comment'})

        self.assertRedirects(response, f'{reverse("login")}?next={detail_url}')
        self.assertFalse(Comment.objects.filter(comment='Anonymous comment').exists())

    def test_edit_comment_rejects_get(self):
        response = self.client.get(reverse('edit_comment', args=[self.parent.id]))

        self.assertEqual(response.status_code, 405)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.comment, 'Parent')

    def test_edit_comment_valid_edit_succeeds(self):
        response = self.client.post(
            reverse('edit_comment', args=[self.parent.id]),
            {'comment': 'Updated parent text'},
            follow=True,
        )

        self.assertRedirects(response, reverse('Blog_detail', args=[self.first_post.slug]))
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.comment, 'Updated parent text')

    def test_edit_comment_rejects_empty_content(self):
        response = self.client.post(
            reverse('edit_comment', args=[self.parent.id]),
            {'comment': '   '},
            follow=True,
        )

        self.assertRedirects(response, reverse('Blog_detail', args=[self.first_post.slug]))
        self.assertContains(response, 'This field is required.')
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.comment, 'Parent')

    def test_edit_comment_by_another_user_is_rejected(self):
        other_user = User.objects.create_user(
            username='other-reader', password='test-password'
        )
        self.client.force_login(other_user)

        response = self.client.post(
            reverse('edit_comment', args=[self.parent.id]),
            {'comment': 'Hijacked text'},
            follow=True,
        )

        self.assertRedirects(response, reverse('Blog_detail', args=[self.first_post.slug]))
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.comment, 'Parent')


class BlogDetailQueryTests(TestCase):
    """Guards against N+1 query regressions on the article detail view."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='detail-author', password='test-password'
        )
        self.category = Category.objects.create(name='Detail Category')
        self.post = Blog.objects.create(
            title='Detail post', slug='detail-post', category=self.category,
            author=self.author, short_description='A short description',
            blog_body='<p>Body</p>', status='published',
        )
        # A second published post in the same category so related_posts
        # actually returns rows.
        Blog.objects.create(
            title='Related post', slug='related-post', category=self.category,
            author=self.author, short_description='Another description',
            blog_body='<p>Related body</p>', status='published',
        )

    def _add_comments_with_replies(self, *, comment_count, replies_per_comment):
        for comment_index in range(comment_count):
            commenter = User.objects.create_user(
                username=f'commenter-{comment_index}-{Comment.objects.count()}',
                password='test-password',
            )
            parent = Comment.objects.create(
                user=commenter, blog=self.post, comment=f'Comment {comment_index}'
            )
            for reply_index in range(replies_per_comment):
                replier = User.objects.create_user(
                    username=f'replier-{comment_index}-{reply_index}-{Comment.objects.count()}',
                    password='test-password',
                )
                Comment.objects.create(
                    user=replier, blog=self.post, parent=parent,
                    comment=f'Reply {comment_index}-{reply_index}',
                )

    def test_detail_page_returns_200_and_renders_related_and_comments(self):
        self._add_comments_with_replies(comment_count=2, replies_per_comment=2)

        response = self.client.get(reverse('Blog_detail', args=[self.post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Related post')
        self.assertContains(response, 'Comment 0')
        self.assertContains(response, 'Reply 0-0')

    def test_detail_query_count_does_not_grow_with_comment_and_reply_count(self):
        # Compare query counts for a small vs. larger set of comments/replies.
        # A per-row query (N+1) would make the larger case scale up sharply;
        # a bounded, resilient upper bound catches that without asserting a
        # brittle exact count.
        self._add_comments_with_replies(comment_count=2, replies_per_comment=2)

        with CaptureQueriesContext(connection) as small_queries:
            response = self.client.get(reverse('Blog_detail', args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)

        self._add_comments_with_replies(comment_count=8, replies_per_comment=3)

        with CaptureQueriesContext(connection) as big_queries:
            response = self.client.get(reverse('Blog_detail', args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)

        self.assertLessEqual(len(big_queries), len(small_queries) + 5)


class CategoryArchiveTests(TestCase):
    """Guards against N+1 regressions and behavior drift on the category archive."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='category-author', password='test-password'
        )
        self.category = Category.objects.create(name='Category Archive Topic')
        self.other_category = Category.objects.create(name='Other Topic')

    def _create_posts(self, count, *, status='published', category=None):
        category = category or self.category
        created = []
        for index in range(count):
            offset = Blog.objects.count()
            created.append(Blog.objects.create(
                title=f'Category post {offset}',
                slug=f'category-post-{offset}',
                category=category,
                author=self.author,
                short_description='A short description',
                blog_body='<p>Body</p>',
                status=status,
            ))
        return created

    def test_category_page_only_shows_published_posts_in_that_category(self):
        self._create_posts(2, status='published')
        self._create_posts(1, status='draft')
        self._create_posts(1, status='published', category=self.other_category)

        response = self.client.get(
            reverse('posts_by_category', args=[self.category.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].paginator.count, 2)
        for post in response.context['posts']:
            self.assertEqual(post.status, 'published')
            self.assertEqual(post.category_id, self.category.id)

    def test_category_page_paginates_correctly(self):
        self._create_posts(9, status='published')

        first_page = self.client.get(
            reverse('posts_by_category', args=[self.category.id])
        )
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.context['posts']), 6)
        self.assertTrue(first_page.context['posts'].has_next())

        second_page = self.client.get(
            reverse('posts_by_category', args=[self.category.id]),
            {'page': 2},
        )
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context['posts']), 3)
        self.assertFalse(second_page.context['posts'].has_next())

    def test_category_page_query_count_does_not_grow_with_post_count(self):
        self._create_posts(3, status='published')

        with CaptureQueriesContext(connection) as small_queries:
            response = self.client.get(
                reverse('posts_by_category', args=[self.category.id])
            )
        self.assertEqual(response.status_code, 200)

        self._create_posts(20, status='published')

        with CaptureQueriesContext(connection) as big_queries:
            response = self.client.get(
                reverse('posts_by_category', args=[self.category.id])
            )
        self.assertEqual(response.status_code, 200)

        self.assertLessEqual(len(big_queries), len(small_queries) + 3)


class AuthorProfileArchiveTests(TestCase):
    """Guards against N+1 regressions and draft leakage on public author pages."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='profile-author', password='test-password'
        )
        self.other_author = User.objects.create_user(
            username='other-profile-author', password='test-password'
        )
        self.category = Category.objects.create(name='Author Archive Topic')

    def _create_posts(self, count, *, status='published', author=None):
        author = author or self.author
        created = []
        for index in range(count):
            offset = Blog.objects.count()
            created.append(Blog.objects.create(
                title=f'Author post {offset}',
                slug=f'author-post-{offset}',
                category=self.category,
                author=author,
                short_description='A short description',
                blog_body='<p>Body</p>',
                status=status,
            ))
        return created

    def test_author_page_excludes_drafts_for_anonymous_visitor(self):
        self._create_posts(2, status='published')
        self._create_posts(1, status='draft')
        self._create_posts(1, status='published', author=self.other_author)

        response = self.client.get(
            reverse('author_profile', args=[self.author.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].paginator.count, 2)
        for post in response.context['posts']:
            self.assertEqual(post.status, 'published')
            self.assertEqual(post.author_id, self.author.id)

    def test_author_page_excludes_drafts_for_other_authenticated_users(self):
        self._create_posts(2, status='published')
        self._create_posts(1, status='draft')
        self.client.force_login(self.other_author)

        response = self.client.get(
            reverse('author_profile', args=[self.author.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].paginator.count, 2)

    def test_author_page_paginates_correctly(self):
        self._create_posts(9, status='published')

        first_page = self.client.get(
            reverse('author_profile', args=[self.author.username])
        )
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.context['posts']), 6)
        self.assertTrue(first_page.context['posts'].has_next())

        second_page = self.client.get(
            reverse('author_profile', args=[self.author.username]),
            {'page': 2},
        )
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context['posts']), 3)
        self.assertFalse(second_page.context['posts'].has_next())

    def test_author_page_query_count_does_not_grow_with_post_count(self):
        self._create_posts(3, status='published')

        with CaptureQueriesContext(connection) as small_queries:
            response = self.client.get(
                reverse('author_profile', args=[self.author.username])
            )
        self.assertEqual(response.status_code, 200)

        self._create_posts(20, status='published')

        with CaptureQueriesContext(connection) as big_queries:
            response = self.client.get(
                reverse('author_profile', args=[self.author.username])
            )
        self.assertEqual(response.status_code, 200)

        self.assertLessEqual(len(big_queries), len(small_queries) + 3)


class CategoryIndexTests(TestCase):
    """Verifies the categories index page (category_index view)."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='index-author', password='test-password'
        )

    def _create_post(self, *, slug, category, status='published'):
        return Blog.objects.create(
            title=f'Post {slug}',
            slug=slug,
            category=category,
            author=self.author,
            short_description='A short description',
            blog_body='<p>Body</p>',
            status=status,
        )

    def test_category_index_url_resolves_and_reverses(self):
        self.assertEqual(reverse('category_index'), '/categories/')

    def test_category_index_does_not_collide_with_dashboard_categories_url(self):
        # The dashboard's category-management list uses the name
        # 'categories' (plural, no underscore); the public index uses
        # 'category_index'. Both must resolve independently.
        self.assertEqual(reverse('categories'), '/dashboard/categories/')
        self.assertEqual(reverse('category_index'), '/categories/')
        self.assertNotEqual(reverse('categories'), reverse('category_index'))

    def test_returns_200_and_uses_categories_template(self):
        response = self.client.get(reverse('category_index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories.html')

    def test_categories_are_ordered_alphabetically(self):
        Category.objects.create(name='Zebra Topic')
        Category.objects.create(name='Apple Topic')
        Category.objects.create(name='Mango Topic')

        response = self.client.get(reverse('category_index'))

        names = [category.name for category in response.context['categories']]
        self.assertEqual(names, ['Apple Topic', 'Mango Topic', 'Zebra Topic'])

    def test_published_post_count_is_accurate_per_category(self):
        busy_category = Category.objects.create(name='Busy Category')
        quiet_category = Category.objects.create(name='Quiet Category')
        self._create_post(slug='busy-1', category=busy_category, status='published')
        self._create_post(slug='busy-2', category=busy_category, status='published')
        self._create_post(slug='quiet-1', category=quiet_category, status='published')

        response = self.client.get(reverse('category_index'))
        counts_by_name = {
            category.name: category.published_post_count
            for category in response.context['categories']
        }

        self.assertEqual(counts_by_name['Busy Category'], 2)
        self.assertEqual(counts_by_name['Quiet Category'], 1)

    def test_draft_posts_are_excluded_from_the_count(self):
        category = Category.objects.create(name='Mixed Category')
        self._create_post(slug='mixed-published', category=category, status='published')
        self._create_post(slug='mixed-draft', category=category, status='draft')

        response = self.client.get(reverse('category_index'))
        category_result = response.context['categories'].get(pk=category.pk)

        self.assertEqual(category_result.published_post_count, 1)

    def test_category_with_zero_published_posts_shows_zero_count(self):
        empty_category = Category.objects.create(name='Empty Category')

        response = self.client.get(reverse('category_index'))
        category_result = response.context['categories'].get(pk=empty_category.pk)

        self.assertEqual(category_result.published_post_count, 0)

    def test_empty_state_renders_when_no_categories_exist(self):
        response = self.client.get(reverse('category_index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No categories yet')

    def test_category_names_and_counts_render_on_page(self):
        category = Category.objects.create(name='Rendered Category')
        self._create_post(slug='rendered-post', category=category, status='published')

        response = self.client.get(reverse('category_index'))

        self.assertContains(response, 'Rendered Category')
        self.assertContains(response, '1')


class GlobalCategoriesContextProcessorTests(TestCase):
    """Verifies caching behavior of the global categories context processor."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_returns_all_categories_in_alphabetical_order(self):
        Category.objects.create(name='Zebra Topic')
        Category.objects.create(name='Apple Topic')
        Category.objects.create(name='Mango Topic')

        context = get_categories(request=None)

        self.assertIn('categories', context)
        names = [category.name for category in context['categories']]
        self.assertEqual(names, ['Apple Topic', 'Mango Topic', 'Zebra Topic'])

    def test_result_is_cached_under_expected_key(self):
        Category.objects.create(name='Cached Topic')

        self.assertIsNone(cache.get(GLOBAL_CATEGORIES_CACHE_KEY))
        get_categories(request=None)

        cached_value = cache.get(GLOBAL_CATEGORIES_CACHE_KEY)
        self.assertIsNotNone(cached_value)
        self.assertEqual([c.name for c in cached_value], ['Cached Topic'])

    def test_repeated_calls_do_not_requery_the_database_once_cached(self):
        Category.objects.create(name='Warm Cache Topic')

        # Prime the cache.
        get_categories(request=None)

        with CaptureQueriesContext(connection) as queries:
            get_categories(request=None)
            get_categories(request=None)

        self.assertEqual(len(queries), 0)

    def test_new_category_is_not_reflected_until_cache_expires(self):
        # This test documents current behavior: cache invalidation on
        # category changes is intentionally out of scope for this task.
        Category.objects.create(name='Original Topic')
        first_result = get_categories(request=None)
        self.assertEqual(len(first_result['categories']), 1)

        Category.objects.create(name='New Topic')
        second_result = get_categories(request=None)

        self.assertEqual(len(second_result['categories']), 1)

    def test_home_page_still_renders_categories_via_context_processor(self):
        Category.objects.create(name='Rendered Topic')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rendered Topic')


class UploadEndpointSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='upload-user', password='test-password'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def image_bytes(self, image_format):
        image = Image.new('RGB', (1, 1), color='white')
        buffer = BytesIO()
        image.save(buffer, format=image_format)
        return buffer.getvalue()

    def test_avatar_uses_the_shared_validator(self):
        spoofed_avatar = SimpleUploadedFile(
            'avatar.jpg', self.image_bytes('PNG'), content_type='image/jpeg'
        )
        form = UserProfileForm(
            data={'first_name': '', 'last_name': '', 'email': '', 'bio': '',
                  'website': '', 'location': ''},
            files={'avatar': spoofed_avatar},
            instance=self.profile,
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_ckeditor_endpoint_rejects_invalid_image_before_storage(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('ck_editor_5_upload_file'),
            {'upload': SimpleUploadedFile(
                'unsafe.svg', b'<svg></svg>', content_type='image/svg+xml'
            )},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('JPEG, PNG, or WebP', response.json()['error']['message'])


class CommentRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='commenter', password='test-password')
        self.other_user = User.objects.create_user(username='other-commenter', password='test-password')
        self.category = Category.objects.create(name='Rate limits')
        self.post = Blog.objects.create(
            title='Rate Limited Post', slug='rate-limited-post', category=self.category,
            author=self.user, short_description='Summary', blog_body='<p>Body</p>',
            status='published',
        )
        self.url = reverse('Blog_detail', args=[self.post.slug])
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_get_does_not_consume_the_comment_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.get(self.url).status_code, 200)
        for number in range(10):
            self.assertEqual(
                self.client.post(self.url, {'comment': f'Comment {number}'}).status_code,
                302,
            )
        self.assertEqual(self.client.post(self.url, {'comment': 'Blocked'}).status_code, 429)

    def test_comment_limit_blocks_the_eleventh_post_with_feedback(self):
        for number in range(10):
            self.client.post(self.url, {'comment': f'Comment {number}'})
        response = self.client.post(self.url, {'comment': 'Blocked comment'})

        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response, 'Too many comment submissions.', status_code=429
        )
        self.assertContains(response, 'Blocked comment', status_code=429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertFalse(Comment.objects.filter(comment='Blocked comment').exists())

    def test_invalid_comment_and_parent_submissions_count(self):
        self.assertEqual(self.client.post(self.url, {'comment': '   '}).status_code, 200)
        for number in range(9):
            self.client.post(
                self.url,
                {'comment': f'Invalid parent {number}', 'parent_id': 'not-an-id'},
            )
        self.assertEqual(self.client.post(self.url, {'comment': 'Blocked'}).status_code, 429)

    def test_authenticated_users_have_separate_comment_buckets(self):
        for number in range(10):
            self.client.post(self.url, {'comment': f'Comment {number}'})
        self.assertEqual(self.client.post(self.url, {'comment': 'Blocked'}).status_code, 429)

        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.post(self.url, {'comment': 'Other user comment'}).status_code,
            302,
        )

    def test_anonymous_post_redirects_without_consuming_a_user_bucket(self):
        self.client.logout()
        response = self.client.post(self.url, {'comment': 'Anonymous comment'})
        self.assertRedirects(response, f'{reverse("login")}?next={self.url}')
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url, {'comment': 'Authenticated'}).status_code, 302)


class PublicationDateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='date-reader')
        self.category = Category.objects.create(name='Dates')
        self.post = Blog.objects.create(
            title='Publication Date Story',
            slug='publication-date-story',
            category=self.category,
            author=self.user,
            short_description='Publication date summary',
            blog_body='<p>Publication date body</p>',
            status='published',
        )

    def test_public_outputs_use_published_at_when_available(self):
        now = timezone.now()
        created_at = now - timedelta(days=10)
        published_at = now - timedelta(days=3)
        updated_at = now - timedelta(days=1)
        Blog.objects.filter(pk=self.post.pk).update(
            created_at=created_at,
            published_at=published_at,
            updated_at=updated_at,
        )

        response = self.client.get(reverse('Blog_detail', args=[self.post.slug]))
        published_label = published_at.strftime('%B %d, %Y').replace(' 0', ' ')
        self.assertContains(response, published_label)
        self.assertContains(response, published_at.isoformat())
        self.assertContains(response, updated_at.isoformat())

        home_response = self.client.get(reverse('home'))
        self.assertContains(home_response, 'Publication Date Story')

    def test_legacy_published_post_falls_back_to_created_at(self):
        created_at = timezone.now() - timedelta(days=7)
        Blog.objects.filter(pk=self.post.pk).update(
            created_at=created_at,
            published_at=None,
        )

        response = self.client.get(reverse('Blog_detail', args=[self.post.slug]))
        created_label = created_at.strftime('%B %d, %Y').replace(' 0', ' ')
        self.assertContains(response, created_label)
        self.assertContains(response, created_at.isoformat())
        self.post.refresh_from_db()
        self.assertEqual(self.post.effective_published_at, created_at)


class SearchRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='searcher')
        self.category = Category.objects.create(name='Search')
        self.published_post = Blog.objects.create(
            title='Searchable Published Story',
            slug='searchable-published-story',
            category=self.category,
            author=self.user,
            short_description='A matching published story',
            blog_body='<p>Published content</p>',
            status='published',
        )
        self.draft_post = Blog.objects.create(
            title='Searchable Draft Story',
            slug='searchable-draft-story',
            category=self.category,
            author=self.user,
            short_description='A matching draft story',
            blog_body='<p>Draft content</p>',
            status='draft',
        )

    def assert_empty_search(self, keyword=None):
        data = {} if keyword is None else {'keyword': keyword}
        response = self.client.get(reverse('search'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No posts found')
        self.assertNotContains(response, self.published_post.title)
        self.assertNotContains(response, self.draft_post.title)

    def test_search_without_keyword_returns_empty_results(self):
        self.assert_empty_search()

    def test_search_with_empty_keyword_returns_empty_results(self):
        self.assert_empty_search('')

    def test_search_with_whitespace_keyword_returns_empty_results(self):
        self.assert_empty_search('   ')

    def test_valid_search_returns_matching_published_post(self):
        response = self.client.get(
            reverse('search'), {'keyword': 'Searchable Published'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.published_post.title)
        self.assertNotContains(response, self.draft_post.title)

    def test_valid_search_excludes_matching_draft(self):
        response = self.client.get(reverse('search'), {'keyword': 'Story'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.draft_post.title)


class PublicAuthorProfileTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='writer', first_name='Ink', last_name='Writer'
        )
        UserProfile.objects.create(
            user=self.author,
            bio='Writing thoughtful essays for curious readers.',
            location='Kathmandu',
            website='https://example.com',
        )
        self.category = Category.objects.create(name='Essays')
        self.published_post = Blog.objects.create(
            title='Public Story', slug='public-story', category=self.category,
            author=self.author, short_description='Public description',
            blog_body='<p>Public body</p>', status='published'
        )
        Blog.objects.create(
            title='Draft Story', slug='draft-story', category=self.category,
            author=self.author, short_description='Draft description',
            blog_body='<p>Draft body</p>', status='draft'
        )

    def test_public_author_page_shows_profile_and_published_posts_only(self):
        response = self.client.get(
            reverse('author_profile', args=[self.author.username])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ink Writer')
        self.assertContains(response, 'Writing thoughtful essays')
        self.assertContains(response, 'Public Story')
        self.assertNotContains(response, 'Draft Story')

    def test_article_byline_links_to_public_author_page(self):
        response = self.client.get(
            reverse('Blog_detail', args=[self.published_post.slug])
        )
        self.assertContains(
            response,
            reverse('author_profile', args=[self.author.username])
        )


class PublishingVisibilityTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='publisher', password='test-password'
        )
        self.other_user = User.objects.create_user(
            username='other', password='test-password'
        )
        self.staff_user = User.objects.create_user(
            username='staff', password='test-password', is_staff=True
        )
        self.category = Category.objects.create(name='Publishing')
        self.published_post = Blog.objects.create(
            title='Visible Published Post',
            slug='visible-published-post',
            category=self.category,
            author=self.author,
            short_description='Visible summary',
            blog_body='<p>Visible body</p>',
            status='published',
        )
        self.draft_post = Blog.objects.create(
            title='Private Draft Post',
            slug='private-draft-post',
            category=self.category,
            author=self.author,
            short_description='Private summary',
            blog_body='<p>Private body</p>',
            status='draft',
        )

    def test_drafts_hidden_from_public_home_search_category_and_author_pages(self):
        checks = [
            self.client.get(reverse('home')),
            self.client.get(reverse('search'), {'keyword': 'Post'}),
            self.client.get(reverse('posts_by_category', args=[self.category.id])),
            self.client.get(reverse('author_profile', args=[self.author.username])),
        ]
        for response in checks:
            with self.subTest(path=response.request['PATH_INFO']):
                self.assertContains(response, 'Visible Published Post')
                self.assertNotContains(response, 'Private Draft Post')

    def test_author_can_preview_own_draft(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse('Blog_detail', args=[self.draft_post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft preview')
        self.assertContains(response, 'Private Draft Post')
        self.draft_post.refresh_from_db()
        self.assertEqual(self.draft_post.views, 0)

    def test_staff_can_preview_draft(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('Blog_detail', args=[self.draft_post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft preview')
        self.draft_post.refresh_from_db()
        self.assertEqual(self.draft_post.views, 0)

    def test_other_users_cannot_preview_private_drafts(self):
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[self.draft_post.slug])).status_code,
            404,
        )
        self.draft_post.refresh_from_db()
        self.assertEqual(self.draft_post.views, 0)
        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[self.draft_post.slug])).status_code,
            404,
        )
        self.draft_post.refresh_from_db()
        self.assertEqual(self.draft_post.views, 0)


class RichTextSanitizationTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='rich-writer', password='test-password'
        )
        self.category = Category.objects.create(name='Rich text')

    def test_sanitizer_preserves_safe_ck_editor_content(self):
        content = (
            '<h2>Heading</h2><p><strong>Bold</strong> and <em>italic</em>.</p>'
            '<blockquote>Quote</blockquote><ul><li>One</li><li>Two</li></ul>'
            '<pre><code>print(1)</code></pre>'
            '<a href="https://example.com">Example</a>'
            '<figure class="image image-style-align-left"><img src="/media/uploads/example.jpg" alt="Example">'
            '<figcaption>Caption</figcaption></figure>'
            '<table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table>'
        )
        sanitized = sanitize_rich_text(content)

        for expected in (
            '<h2>Heading</h2>', '<strong>Bold</strong>', '<em>italic</em>',
            '<blockquote>Quote</blockquote>', '<ul><li>One</li><li>Two</li></ul>',
            '<pre><code>print(1)</code></pre>', 'href="https://example.com"',
            'src="/media/uploads/example.jpg"', 'alt="Example"',
            'class="image image-style-align-left"', 'colspan="2"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, sanitized)

    def test_sanitizer_removes_executable_html_attributes_and_urls(self):
        content = (
            '<script>alert(1)</script><p onclick="alert(1)">Text</p>'
            '<img src="x" ONERROR="alert(1)">'
            '<a href="JaVaScRiPt:alert(1)">Bad</a>'
            '<a href="&#106;avascript:alert(1)">Encoded</a>'
            '<img src="data:image/svg+xml;base64,evil" alt="Bad">'
            '<iframe src="https://example.com">frame</iframe><svg onload="alert(1)"></svg>'
            '<p style="color:red">Styled</p>'
        )
        sanitized = sanitize_rich_text(content)
        lowered = sanitized.lower()

        for unsafe in ('<script', 'alert(1)', 'onclick', 'onerror', 'javascript:', 'data:', '<iframe', '<svg', 'style='):
            with self.subTest(unsafe=unsafe):
                self.assertNotIn(unsafe, lowered)
        self.assertIn('<p>Text</p>', sanitized)
        self.assertIn('>Bad</a>', sanitized)
        self.assertIn('>Encoded</a>', sanitized)

    def test_legacy_article_html_is_sanitized_at_render_time(self):
        post = Blog.objects.create(
            title='Legacy unsafe post', slug='legacy-unsafe-post',
            category=self.category, author=self.author,
            short_description='Legacy summary',
            blog_body='<p>Safe text</p><script>alert(1)</script><img src="x" onerror="alert(1)">',
            status='published',
        )
        response = self.client.get(reverse('Blog_detail', args=[post.slug]))
        content = response.content.decode().lower()

        self.assertEqual(response.status_code, 200)
        self.assertIn('<p>safe text</p>', content)
        self.assertNotIn('<script>alert(1)</script>', content)
        self.assertNotIn('onerror=', content)
        self.assertNotIn('alert(1)', content)

    def test_article_template_uses_sanitizing_filter_not_raw_safe(self):
        template = (Path(__file__).resolve().parent.parent / 'templates' / 'blog_detail.html').read_text()
        self.assertIn('post.blog_body|sanitize_rich_text', template)
        self.assertNotIn('post.blog_body|safe', template)

    def test_admin_form_uses_the_same_storage_sanitization_policy(self):
        form = BlogAdminForm(data={
            'title': 'Admin rich text',
            'slug': 'admin-rich-text',
            'category': self.category.id,
            'author': self.author.id,
            'short_description': 'Admin summary',
            'blog_body': '<p>Admin content</p><script>alert(1)</script>',
            'status': 'draft',
            'is_featured': False,
            'views': 0,
            'featured_image_alt': '',
            'meta_description': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        post = form.save()
        self.assertEqual(post.blog_body, '<p>Admin content</p>')
