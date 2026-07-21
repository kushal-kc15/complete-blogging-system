from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.utils import timezone
from datetime import timedelta
from pathlib import Path

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
