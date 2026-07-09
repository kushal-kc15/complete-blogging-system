from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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

    def test_staff_can_preview_draft(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('Blog_detail', args=[self.draft_post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft preview')

    def test_other_users_cannot_preview_private_drafts(self):
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[self.draft_post.slug])).status_code,
            404,
        )
        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.get(reverse('Blog_detail', args=[self.draft_post.slug])).status_code,
            404,
        )
