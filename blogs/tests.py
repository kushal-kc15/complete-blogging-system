from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .forms import CommentForm
from .models import Blog, Bookmark, Category, Comment, Like, UserProfile


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
