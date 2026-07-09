from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from io import BytesIO
from PIL import Image

from blogs.models import Blog, Category, UserProfile


class SEOOperationsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='writer')
        self.category = Category.objects.create(name='SEO')
        self.published_post = Blog.objects.create(
            title='Published SEO Post',
            slug='published-seo-post',
            category=self.category,
            author=self.author,
            short_description='Published summary',
            blog_body='<p>Published body</p>',
            status='published',
        )
        self.draft_post = Blog.objects.create(
            title='Draft SEO Post',
            slug='draft-seo-post',
            category=self.category,
            author=self.author,
            short_description='Draft summary',
            blog_body='<p>Draft body</p>',
            status='draft',
        )

    def test_robots_txt_has_public_and_private_rules(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        content = response.content.decode()
        self.assertIn('Allow: /sitemap.xml', content)
        self.assertIn('Allow: /feed/', content)
        self.assertIn('Disallow: /dashboard/', content)
        self.assertIn('Disallow: /admin/', content)
        self.assertIn('Disallow: /blogs/search/', content)
        self.assertIn('Sitemap: http://testserver/sitemap.xml', content)

    def test_sitemap_includes_only_published_posts(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.published_post.slug, content)
        self.assertNotIn(self.draft_post.slug, content)

    def test_feed_includes_only_published_posts(self):
        response = self.client.get(reverse('rss_feed'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Published SEO Post', content)
        self.assertNotIn('Draft SEO Post', content)


class AuthProfileCoreTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reader',
            password='test-password',
            email='reader@example.com',
        )
        UserProfile.objects.create(user=self.user)

    def image_bytes(self, image_format='GIF'):
        image = Image.new('RGB', (1, 1), color='white')
        buffer = BytesIO()
        image.save(buffer, format=image_format)
        return buffer.getvalue()

    def test_login_respects_safe_next_redirect(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'reader',
                'password': 'test-password',
                'next': reverse('profile'),
            },
        )
        self.assertRedirects(response, reverse('profile'))

    def test_login_rejects_unsafe_next_redirect(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'reader',
                'password': 'test-password',
                'next': 'https://evil.example/profile',
            },
        )
        self.assertRedirects(response, reverse('home'))

    def test_password_reset_page_renders_clean_text(self):
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "we'll send you reset instructions")
        self.assertNotContains(response, 'â')

    def test_invalid_avatar_upload_is_rejected(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile(
            'avatar.gif',
            self.image_bytes('GIF'),
            content_type='image/gif',
        )
        response = self.client.post(
            reverse('edit_profile'),
            {
                'first_name': 'Reader',
                'last_name': '',
                'bio': '',
                'website': '',
                'location': '',
                'avatar': upload,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload a JPEG, PNG, or WebP avatar image.')
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    def test_register_normalizes_email_and_rejects_case_duplicate(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newreader',
                'email': 'NewReader@Example.COM',
                'password1': 'StrongPass12345!',
                'password2': 'StrongPass12345!',
            },
        )
        self.assertRedirects(response, reverse('login'))
        self.assertEqual(
            User.objects.get(username='newreader').email,
            'newreader@example.com',
        )

        response = self.client.post(
            reverse('register'),
            {
                'username': 'duplicate',
                'email': 'NEWREADER@example.com',
                'password1': 'StrongPass12345!',
                'password2': 'StrongPass12345!',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This email is already registered.')
        self.assertFalse(User.objects.filter(username='duplicate').exists())

    def test_profile_email_update_normalizes_and_rejects_case_duplicate(self):
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='test-password',
        )
        UserProfile.objects.create(user=other_user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('edit_profile'),
            {
                'first_name': 'Reader',
                'last_name': 'One',
                'email': 'ReaderNew@Example.COM',
                'bio': '',
                'website': '',
                'location': '',
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'readernew@example.com')

        response = self.client.post(
            reverse('edit_profile'),
            {
                'first_name': 'Reader',
                'last_name': 'One',
                'email': 'OTHER@EXAMPLE.COM',
                'bio': '',
                'website': '',
                'location': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This email is already registered.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'readernew@example.com')
