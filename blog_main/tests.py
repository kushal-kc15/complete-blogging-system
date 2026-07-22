import importlib
import os
import sys
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core import mail
from django.http import HttpResponse
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.security import SecurityMiddleware
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from PIL import Image
from unittest.mock import patch

from django.test.utils import CaptureQueriesContext
from django.db import connection

from blogs.forms import ContactForm
from blogs.models import Blog, Category, Contact, UserProfile
from blog_main.middleware import SecurityHeadersMiddleware
from blog_main.views import HOME_FEATURED_POST_LIMIT, HOME_TOP_CATEGORIES_LIMIT
from .feeds import LatestPostsFeed


class Custom404Tests(TestCase):
    @override_settings(DEBUG=False)
    def test_custom_404_page_uses_readable_navigation_text(self):
        response = self.client.get('/route-that-does-not-exist-404/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Go to homepage', status_code=404)
        self.assertNotContains(response, 'youâ€™re', status_code=404)


class ContactRouteTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_contact_name_resolves_to_canonical_route(self):
        self.assertEqual(reverse('contact'), '/contact/')

    def test_canonical_contact_page_uses_existing_template(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')
        self.assertIsInstance(response.context['form'], ContactForm)

    def test_accidental_category_contact_route_is_not_available(self):
        response = self.client.get('/category/contact/')

        self.assertEqual(response.status_code, 404)

    def test_contact_submission_still_works_on_canonical_route(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Reader',
                'email': 'reader@example.com',
                'subject': 'Hello',
                'message': 'A contact message',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertContains(response, "Thank you for your message")
        self.assertEqual(Contact.objects.count(), 1)
        contact = Contact.objects.get()
        self.assertEqual(contact.name, 'Reader')
        self.assertEqual(contact.email, 'reader@example.com')
        self.assertEqual(contact.subject, 'Hello')
        self.assertEqual(contact.message, 'A contact message')

    def test_invalid_email_is_rejected_without_creating_contact(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Reader',
                'email': 'invalid-email',
                'subject': 'Question',
                'message': 'Please help.',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid email address.')
        self.assertContains(response, 'value="Reader"')
        self.assertContains(response, 'value="Question"')
        self.assertEqual(Contact.objects.count(), 0)

    def test_missing_required_field_is_rejected_without_creating_contact(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Reader',
                'email': 'reader@example.com',
                'subject': '',
                'message': 'Please help.',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Contact.objects.count(), 0)

    def test_whitespace_only_required_fields_are_rejected(self):
        valid_data = {
            'name': 'Reader',
            'email': 'reader@example.com',
            'subject': 'Question',
            'message': 'Please help.',
        }
        for field_name in ('name', 'subject', 'message'):
            data = valid_data.copy()
            data[field_name] = '   '
            with self.subTest(field=field_name):
                response = self.client.post(reverse('contact'), data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This field is required.')
                self.assertEqual(Contact.objects.count(), 0)


class HomeViewTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='home-author', password='test-password'
        )
        self.category = Category.objects.create(name='Home Category')

    def _create_post(self, *, slug, is_featured, status='published'):
        return Blog.objects.create(
            title=f'Post {slug}',
            slug=slug,
            category=self.category,
            author=self.author,
            short_description='A short description',
            blog_body='<p>Body</p>',
            status=status,
            is_featured=is_featured,
        )

    def test_home_returns_200_when_empty(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        # Requirement 3.4: with zero featured posts the hero is NOT rendered;
        # instead a named "Featured story" empty-state states what is missing,
        # regardless of whether other non-featured posts exist.
        self.assertContains(response, 'Featured story')
        self.assertContains(response, 'No featured story yet')
        self.assertContains(response, 'No posts yet')

    def test_home_shows_featured_and_latest_sections(self):
        self._create_post(slug='featured-post', is_featured=True)
        self._create_post(slug='latest-post', is_featured=False)
        # A draft must never appear on the public homepage.
        self._create_post(slug='draft-post', is_featured=False, status='draft')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Post featured-post')
        self.assertContains(response, 'Post latest-post')
        self.assertNotContains(response, 'Post draft-post')

    def test_home_featured_posts_are_limited(self):
        for index in range(HOME_FEATURED_POST_LIMIT + 5):
            self._create_post(slug=f'featured-{index}', is_featured=True)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['featured_post']), HOME_FEATURED_POST_LIMIT)

    def test_home_query_count_does_not_grow_with_post_count(self):
        # Guard against N+1 queries on author/category access without
        # asserting a brittle exact count: the number of queries for a
        # larger set of posts should not exceed the count for a smaller
        # set, which would indicate a per-row query.
        for index in range(3):
            self._create_post(slug=f'small-featured-{index}', is_featured=True)
            self._create_post(slug=f'small-latest-{index}', is_featured=False)

        with CaptureQueriesContext(connection) as small_queries:
            response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

        for index in range(3, 15):
            self._create_post(slug=f'big-featured-{index}', is_featured=True)
            self._create_post(slug=f'big-latest-{index}', is_featured=False)

        with CaptureQueriesContext(connection) as big_queries:
            response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

        self.assertLessEqual(len(big_queries), len(small_queries) + 5)

    def test_top_categories_present_in_homepage_context(self):
        self._create_post(slug='top-category-post', is_featured=False)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('top_categories', response.context)

    def test_top_categories_ordered_by_published_post_count_descending(self):
        busy_category = Category.objects.create(name='Busy Category')
        quiet_category = Category.objects.create(name='Quiet Category')
        for index in range(3):
            Blog.objects.create(
                title=f'Busy post {index}', slug=f'busy-post-{index}',
                category=busy_category, author=self.author,
                short_description='Summary', blog_body='<p>Body</p>',
                status='published',
            )
        Blog.objects.create(
            title='Quiet post', slug='quiet-post', category=quiet_category,
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='published',
        )

        response = self.client.get(reverse('home'))
        names = [category.name for category in response.context['top_categories']]

        self.assertEqual(names, ['Busy Category', 'Quiet Category'])

    def test_top_categories_alphabetical_tie_break_on_equal_count(self):
        zebra_category = Category.objects.create(name='Zebra Category')
        apple_category = Category.objects.create(name='Apple Category')
        Blog.objects.create(
            title='Zebra post', slug='zebra-post', category=zebra_category,
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='published',
        )
        Blog.objects.create(
            title='Apple post', slug='apple-post', category=apple_category,
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='published',
        )

        response = self.client.get(reverse('home'))
        names = [category.name for category in response.context['top_categories']]

        # Both categories have exactly one published post; the alphabetical
        # tie-break must place 'Apple Category' before 'Zebra Category'.
        self.assertEqual(names, ['Apple Category', 'Zebra Category'])

    def test_top_categories_excludes_draft_posts_from_count(self):
        category = Category.objects.create(name='Mixed Status Category')
        Blog.objects.create(
            title='Published post', slug='mixed-published', category=category,
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='published',
        )
        Blog.objects.create(
            title='Draft post', slug='mixed-draft', category=category,
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='draft',
        )

        response = self.client.get(reverse('home'))
        top_categories = {
            category.name: category.published_post_count
            for category in response.context['top_categories']
        }

        self.assertEqual(top_categories['Mixed Status Category'], 1)

    def test_top_categories_excludes_categories_with_zero_published_posts(self):
        Category.objects.create(name='Draft Only Category')
        published_category = Category.objects.create(name='Published Category')
        Blog.objects.create(
            title='Draft only post', slug='draft-only-post',
            category=Category.objects.get(name='Draft Only Category'),
            author=self.author, short_description='Summary',
            blog_body='<p>Body</p>', status='draft',
        )
        Blog.objects.create(
            title='Published post', slug='published-post-only',
            category=published_category, author=self.author,
            short_description='Summary', blog_body='<p>Body</p>',
            status='published',
        )

        response = self.client.get(reverse('home'))
        names = [category.name for category in response.context['top_categories']]

        self.assertIn('Published Category', names)
        self.assertNotIn('Draft Only Category', names)

    def test_top_categories_limited_to_eight(self):
        for index in range(HOME_TOP_CATEGORIES_LIMIT + 5):
            category = Category.objects.create(name=f'Category {index:02d}')
            Blog.objects.create(
                title=f'Post {index}', slug=f'category-post-{index}',
                category=category, author=self.author,
                short_description='Summary', blog_body='<p>Body</p>',
                status='published',
            )

        response = self.client.get(reverse('home'))

        self.assertEqual(
            len(response.context['top_categories']), HOME_TOP_CATEGORIES_LIMIT
        )


class ContactRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('contact')
        self.data = {
            'name': 'Reader',
            'email': 'reader@example.com',
            'subject': 'Question',
            'message': 'Please help.',
        }

    def tearDown(self):
        cache.clear()

    def test_get_does_not_consume_the_contact_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.get(self.url).status_code, 200)
        for _ in range(5):
            self.assertEqual(self.client.post(self.url, self.data).status_code, 302)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 429)

    def test_contact_limit_blocks_the_sixth_post_with_feedback(self):
        for _ in range(5):
            self.client.post(self.url, self.data)
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response, 'Too many contact submissions.', status_code=429
        )
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(Contact.objects.count(), 5)

    def test_invalid_contact_submissions_count_and_ips_have_separate_buckets(self):
        invalid_data = self.data | {'email': 'invalid-email'}
        self.assertEqual(self.client.post(self.url, invalid_data).status_code, 200)
        for _ in range(4):
            self.client.post(self.url, self.data)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 429)

        response = self.client.post(
            self.url, self.data, REMOTE_ADDR='203.0.113.10'
        )
        self.assertEqual(response.status_code, 302)


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

    def test_feed_uses_effective_published_date(self):
        published_at = timezone.now() - timedelta(days=4)
        Blog.objects.filter(pk=self.published_post.pk).update(
            published_at=published_at
        )
        self.published_post.refresh_from_db()

        self.assertEqual(
            LatestPostsFeed().item_pubdate(self.published_post), published_at
        )


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
        self.assertContains(
            response, 'Upload a JPEG, PNG, or WebP image with a valid extension.'
        )
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

    def test_login_page_includes_google_auth_option(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue with Google')
        self.assertContains(response, '/accounts/google/login/')

    def test_register_page_includes_google_auth_option(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue with Google')
        self.assertContains(response, '/accounts/google/login/')


class LoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='reader', password='test-password'
        )
        self.url = reverse('login')

    def tearDown(self):
        cache.clear()

    def failed_login(self, username='reader', *, remote_addr=None):
        extra = {'REMOTE_ADDR': remote_addr} if remote_addr else {}
        return self.client.post(
            self.url,
            {'username': username, 'password': 'wrong-password'},
            **extra,
        )

    def test_get_requests_do_not_consume_failure_limits(self):
        for _ in range(3):
            self.assertEqual(self.client.get(self.url).status_code, 200)
        for _ in range(5):
            self.assertEqual(self.failed_login().status_code, 200)
        self.assertEqual(self.failed_login().status_code, 429)

    def test_successful_login_does_not_consume_failure_limits_or_change_next(self):
        response = self.client.post(
            self.url,
            {
                'username': 'reader',
                'password': 'test-password',
                'next': reverse('profile'),
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.client.logout()
        for _ in range(5):
            self.assertEqual(self.failed_login().status_code, 200)
        self.assertEqual(self.failed_login().status_code, 429)

    def test_identity_limit_returns_429_without_authenticating_or_echoing_password(self):
        for _ in range(5):
            self.assertEqual(self.failed_login().status_code, 200)
        self.assertEqual(self.failed_login().status_code, 429)
        with patch.object(AuthenticationForm, 'is_valid') as is_valid:
            response = self.failed_login()

        self.assertEqual(response.status_code, 429)
        self.assertFalse(is_valid.called)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(
            response,
            'Too many unsuccessful login attempts. Please wait and try again.',
            status_code=429,
        )
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertNotContains(response, 'wrong-password', status_code=429)

    def test_username_normalization_and_ip_scoping(self):
        for username in (' Reader ', 'READER', 'reader', 'Reader', ' reader '):
            self.assertEqual(self.failed_login(username).status_code, 200)
        self.assertEqual(self.failed_login('READER').status_code, 429)
        self.assertEqual(
            self.failed_login('reader', remote_addr='203.0.113.10').status_code,
            200,
        )

    def test_different_identities_and_ips_have_separate_buckets(self):
        for _ in range(5):
            self.assertEqual(self.failed_login('first').status_code, 200)
        self.assertEqual(self.failed_login('second').status_code, 200)

        cache.clear()
        for number in range(20):
            self.assertEqual(self.failed_login(f'ip-test-{number}').status_code, 200)
        self.assertEqual(self.failed_login('ip-test-blocked').status_code, 429)
        self.assertEqual(
            self.failed_login('ip-test-blocked', remote_addr='203.0.113.20').status_code,
            200,
        )

    def test_unsafe_next_and_generic_invalid_credentials_behavior_remain(self):
        response = self.client.post(
            self.url,
            {
                'username': 'unknown-user',
                'password': 'wrong-password',
                'next': 'https://evil.example/profile',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please check your username and password.")
        self.assertNotContains(response, 'unknown-user does not exist')


class PasswordResetRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='reset-reader',
            email='reader@example.com',
            password='test-password',
        )
        self.inactive_user = User.objects.create_user(
            username='inactive-reader',
            email='inactive@example.com',
            password='test-password',
            is_active=False,
        )
        self.url = reverse('password_reset')

    def tearDown(self):
        cache.clear()

    def request_reset(self, email, *, remote_addr=None):
        extra = {'REMOTE_ADDR': remote_addr} if remote_addr else {}
        return self.client.post(self.url, {'email': email}, **extra)

    def test_get_requests_do_not_consume_the_reset_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.get(self.url).status_code, 200)
        for _ in range(5):
            self.assertRedirects(
                self.request_reset('unknown@example.com'),
                reverse('password_reset_done'),
            )
        self.assertEqual(self.request_reset('unknown@example.com').status_code, 429)

    def test_known_unknown_and_inactive_emails_have_identical_outward_behavior(self):
        responses = [
            self.request_reset('reader@example.com'),
            self.request_reset('unknown@example.com'),
            self.request_reset('inactive@example.com'),
        ]
        for response in responses:
            self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

    def test_sixth_reset_request_is_limited_without_leaking_account_existence(self):
        for _ in range(5):
            self.assertRedirects(
                self.request_reset('unknown@example.com'),
                reverse('password_reset_done'),
            )

        existing_response = self.request_reset('reader@example.com')
        unknown_response = self.request_reset('unknown@example.com')
        for response in (existing_response, unknown_response):
            self.assertEqual(response.status_code, 429)
            self.assertContains(
                response,
                'Too many password reset requests. Please wait and try again.',
                status_code=429,
            )
            self.assertGreater(int(response['Retry-After']), 0)

    def test_different_ips_have_separate_reset_buckets(self):
        for _ in range(5):
            self.request_reset('unknown@example.com')
        self.assertEqual(self.request_reset('unknown@example.com').status_code, 429)
        self.assertRedirects(
            self.request_reset('unknown@example.com', remote_addr='203.0.113.30'),
            reverse('password_reset_done'),
        )


class ProductionSettingsTests(SimpleTestCase):
    def load_production_settings(self, environment=None, remove=()):
        values = {
            'DJANGO_SECRET_KEY': 'test-production-secret',
            'DJANGO_ALLOWED_HOSTS': 'example.com',
            'POSTGRES_DB': 'inkspire',
            'POSTGRES_USER': 'inkspire_user',
            'POSTGRES_PASSWORD': 'test-password',
            'POSTGRES_HOST': 'db.example.com',
            'POSTGRES_PORT': '5432',
            'REDIS_URL': 'redis://cache.example.com:6379/1',
            'EMAIL_HOST': 'smtp.example.com',
            'EMAIL_PORT': '587',
            'EMAIL_HOST_USER': 'smtp-user',
            'EMAIL_HOST_PASSWORD': 'test-password',
            'DEFAULT_FROM_EMAIL': 'no-reply@example.com',
        }
        values.update(environment or {})
        for name in remove:
            values.pop(name, None)
        with patch.dict(os.environ, values, clear=True), patch(
            'dotenv.load_dotenv', return_value=False
        ):
            sys.modules.pop('blog_main.settings_prod', None)
            return importlib.import_module('blog_main.settings_prod')

    def test_production_debug_is_disabled_and_uses_environment_secret(self):
        production = self.load_production_settings(
            {'DJANGO_SECRET_KEY': 'distinct-production-secret'}
        )
        development = importlib.import_module('blog_main.settings')

        self.assertFalse(production.DEBUG)
        self.assertEqual(production.SECRET_KEY, 'distinct-production-secret')
        self.assertNotEqual(production.SECRET_KEY, development.SECRET_KEY)

    def test_missing_or_blank_production_secret_is_rejected(self):
        for value in (None, ''):
            environment = {}
            if value is not None:
                environment['DJANGO_SECRET_KEY'] = value
            else:
                environment['DJANGO_ALLOWED_HOSTS'] = 'example.com'
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                if value is None:
                    with patch.dict(
                        os.environ,
                        {'DJANGO_ALLOWED_HOSTS': 'example.com'},
                        clear=True,
                    ), patch('dotenv.load_dotenv', return_value=False):
                        sys.modules.pop('blog_main.settings_prod', None)
                        importlib.import_module('blog_main.settings_prod')
                else:
                    self.load_production_settings(environment)

    def test_allowed_hosts_are_cleaned_and_required(self):
        production = self.load_production_settings(
            {'DJANGO_ALLOWED_HOSTS': ' example.com, ,*, www.example.com '}
        )
        self.assertEqual(production.ALLOWED_HOSTS, ['example.com', 'www.example.com'])
        self.assertNotIn('*', production.ALLOWED_HOSTS)

        for value in ('', ' , '):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'DJANGO_ALLOWED_HOSTS': value})

    def test_csrf_origins_are_parsed_and_must_include_a_scheme(self):
        production = self.load_production_settings(
            {
                'DJANGO_CSRF_TRUSTED_ORIGINS': (
                    ' https://example.com, ,https://www.example.com '
                )
            }
        )
        self.assertEqual(
            production.CSRF_TRUSTED_ORIGINS,
            ['https://example.com', 'https://www.example.com'],
        )
        with self.assertRaises(ImproperlyConfigured):
            self.load_production_settings(
                {'DJANGO_CSRF_TRUSTED_ORIGINS': 'example.com'}
            )

    def test_existing_production_security_settings_remain_enabled(self):
        production = self.load_production_settings()
        self.assertTrue(production.SECURE_SSL_REDIRECT)
        self.assertTrue(production.SESSION_COOKIE_SECURE)
        self.assertTrue(production.CSRF_COOKIE_SECURE)
        self.assertTrue(production.SECURE_HSTS_SECONDS)
        self.assertTrue(production.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertTrue(production.SECURE_HSTS_PRELOAD)
        self.assertTrue(production.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(production.X_FRAME_OPTIONS, 'DENY')

    def test_production_security_header_settings_are_configured(self):
        production = self.load_production_settings()

        self.assertEqual(
            production.SECURE_REFERRER_POLICY,
            'strict-origin-when-cross-origin',
        )
        self.assertEqual(production.SECURE_CROSS_ORIGIN_OPENER_POLICY, 'same-origin')
        self.assertEqual(production.SECURE_CROSS_ORIGIN_RESOURCE_POLICY, 'same-origin')
        self.assertIn("default-src 'self'", production.CONTENT_SECURITY_POLICY)
        self.assertIn("script-src 'self' https://cdn.jsdelivr.net", production.CONTENT_SECURITY_POLICY)

    def test_development_does_not_enable_production_hsts_or_csp_middleware(self):
        development = importlib.import_module('blog_main.settings')

        self.assertEqual(getattr(development, 'SECURE_HSTS_SECONDS', 0), 0)
        self.assertNotIn(
            'blog_main.middleware.SecurityHeadersMiddleware',
            development.MIDDLEWARE,
        )

    @override_settings(
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
        SECURE_CONTENT_TYPE_NOSNIFF=True,
        SECURE_REFERRER_POLICY='strict-origin-when-cross-origin',
        SECURE_CROSS_ORIGIN_OPENER_POLICY='same-origin',
        SECURE_CROSS_ORIGIN_RESOURCE_POLICY='same-origin',
        X_FRAME_OPTIONS='DENY',
        CONTENT_SECURITY_POLICY=(
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net"
        ),
    )
    def test_production_security_headers_are_returned_and_hsts_is_secure_only(self):
        handler = SecurityMiddleware(
            XFrameOptionsMiddleware(SecurityHeadersMiddleware(HttpResponse))
        )
        factory = RequestFactory()

        secure_response = handler(factory.get('/', secure=True))
        insecure_response = handler(factory.get('/'))

        self.assertEqual(secure_response['X-Frame-Options'], 'DENY')
        self.assertEqual(secure_response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(
            secure_response['Referrer-Policy'], 'strict-origin-when-cross-origin'
        )
        self.assertEqual(
            secure_response['Permissions-Policy'],
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()',
        )
        self.assertIn("default-src 'self'", secure_response['Content-Security-Policy'])
        self.assertEqual(secure_response['Cross-Origin-Opener-Policy'], 'same-origin')
        self.assertEqual(secure_response['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertIn('Strict-Transport-Security', secure_response)
        self.assertNotIn('Strict-Transport-Security', insecure_response)

    def test_development_uses_sqlite_and_production_requires_postgresql(self):
        development = importlib.import_module('blog_main.settings')
        production = self.load_production_settings()

        self.assertEqual(development.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(production.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        self.assertNotEqual(production.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')

    def test_development_uses_local_memory_cache_and_production_uses_redis(self):
        development = importlib.import_module('blog_main.settings')
        production = self.load_production_settings()

        self.assertEqual(
            development.CACHES['default']['BACKEND'],
            'django.core.cache.backends.locmem.LocMemCache',
        )
        self.assertEqual(
            production.CACHES['default']['BACKEND'],
            'django.core.cache.backends.redis.RedisCache',
        )
        self.assertEqual(
            production.CACHES['default']['LOCATION'],
            'redis://cache.example.com:6379/1',
        )

    def test_production_accepts_redis_and_rediss_urls(self):
        for url in (
            ' redis://cache.example.com:6379/1 ',
            ' rediss://cache.example.com:6380/1 ',
        ):
            with self.subTest(url=url):
                production = self.load_production_settings({'REDIS_URL': url})
                self.assertEqual(production.REDIS_URL, url.strip())

    def test_missing_blank_and_unsupported_redis_urls_are_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load_production_settings(remove=('REDIS_URL',))
        for url in ('   ', 'http://cache.example.com:6379/1'):
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'REDIS_URL': url})

    def test_production_cache_timeout_and_key_prefix_validation(self):
        production = self.load_production_settings()
        self.assertEqual(production.CACHE_DEFAULT_TIMEOUT, 300)
        self.assertEqual(production.CACHE_KEY_PREFIX, 'inkspire')

        production = self.load_production_settings(
            {'CACHE_DEFAULT_TIMEOUT': ' 120 ', 'CACHE_KEY_PREFIX': ' blog '}
        )
        self.assertEqual(production.CACHE_DEFAULT_TIMEOUT, 120)
        self.assertEqual(production.CACHE_KEY_PREFIX, 'blog')

        for timeout in ('invalid', '0', '-1'):
            with self.subTest(timeout=timeout), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'CACHE_DEFAULT_TIMEOUT': timeout})

    def test_postgresql_settings_map_trimmed_required_environment_values(self):
        production = self.load_production_settings(
            {
                'POSTGRES_DB': ' inkspire_db ',
                'POSTGRES_USER': ' inkspire_user ',
                'POSTGRES_PASSWORD': ' secure-password ',
                'POSTGRES_HOST': ' db.example.com ',
                'POSTGRES_PORT': ' 5433 ',
            }
        )
        database = production.DATABASES['default']

        self.assertEqual(database['NAME'], 'inkspire_db')
        self.assertEqual(database['USER'], 'inkspire_user')
        self.assertEqual(database['PASSWORD'], 'secure-password')
        self.assertEqual(database['HOST'], 'db.example.com')
        self.assertEqual(database['PORT'], 5433)
        self.assertTrue(database['CONN_HEALTH_CHECKS'])

    def test_missing_or_blank_postgresql_values_are_rejected(self):
        required_names = (
            'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
            'POSTGRES_HOST', 'POSTGRES_PORT',
        )
        for name in required_names:
            with self.subTest(name=name, state='missing'), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings(remove=(name,))
            with self.subTest(name=name, state='blank'), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({name: '   '})

    def test_postgresql_port_validation(self):
        for value in ('not-a-port', '0', '65536'):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'POSTGRES_PORT': value})

    def test_connection_age_and_sslmode_validation(self):
        production = self.load_production_settings()
        self.assertEqual(production.DATABASES['default']['CONN_MAX_AGE'], 60)
        self.assertEqual(production.DATABASES['default']['OPTIONS']['sslmode'], 'require')

        production = self.load_production_settings(
            {'POSTGRES_CONN_MAX_AGE': '120', 'POSTGRES_SSLMODE': 'verify-full'}
        )
        self.assertEqual(production.DATABASES['default']['CONN_MAX_AGE'], 120)
        self.assertEqual(production.DATABASES['default']['OPTIONS']['sslmode'], 'verify-full')

        for value in ('-1', 'invalid'):
            with self.subTest(connection_age=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'POSTGRES_CONN_MAX_AGE': value})
        for sslmode in ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'):
            with self.subTest(sslmode=sslmode):
                self.assertEqual(
                    self.load_production_settings({'POSTGRES_SSLMODE': sslmode})
                    .DATABASES['default']['OPTIONS']['sslmode'],
                    sslmode,
                )
        with self.assertRaises(ImproperlyConfigured):
            self.load_production_settings({'POSTGRES_SSLMODE': 'invalid'})

    def test_development_uses_console_email_and_production_uses_smtp(self):
        development = importlib.import_module('blog_main.settings')
        production = self.load_production_settings()

        self.assertEqual(
            development.EMAIL_BACKEND,
            'django.core.mail.backends.console.EmailBackend',
        )
        self.assertEqual(
            production.EMAIL_BACKEND,
            'django.core.mail.backends.smtp.EmailBackend',
        )

    def test_production_smtp_settings_map_trimmed_required_values(self):
        production = self.load_production_settings(
            {
                'EMAIL_HOST': ' smtp.example.com ',
                'EMAIL_PORT': ' 465 ',
                'EMAIL_HOST_USER': ' smtp-user ',
                'EMAIL_HOST_PASSWORD': ' smtp-password ',
                'DEFAULT_FROM_EMAIL': ' no-reply@example.com ',
                'SERVER_EMAIL': ' errors@example.com ',
                'EMAIL_USE_TLS': 'off',
                'EMAIL_USE_SSL': 'yes',
                'EMAIL_TIMEOUT': ' 20 ',
                'EMAIL_SUBJECT_PREFIX': ' [InkSpire Production] ',
            }
        )

        self.assertEqual(production.EMAIL_HOST, 'smtp.example.com')
        self.assertEqual(production.EMAIL_PORT, 465)
        self.assertEqual(production.EMAIL_HOST_USER, 'smtp-user')
        self.assertEqual(production.EMAIL_HOST_PASSWORD, 'smtp-password')
        self.assertEqual(production.DEFAULT_FROM_EMAIL, 'no-reply@example.com')
        self.assertEqual(production.SERVER_EMAIL, 'errors@example.com')
        self.assertFalse(production.EMAIL_USE_TLS)
        self.assertTrue(production.EMAIL_USE_SSL)
        self.assertEqual(production.EMAIL_TIMEOUT, 20)
        self.assertEqual(production.EMAIL_SUBJECT_PREFIX, '[InkSpire Production]')

    def test_missing_or_blank_smtp_values_are_rejected(self):
        required_names = (
            'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL',
        )
        for name in required_names:
            with self.subTest(name=name, state='missing'), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings(remove=(name,))
            with self.subTest(name=name, state='blank'), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({name: '   '})

    def test_smtp_port_boolean_timeout_and_sender_validation(self):
        for value in ('invalid', '0', '-1', '65536'):
            with self.subTest(port=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'EMAIL_PORT': value})
        for value, expected in (
            ('true', True), ('1', True), ('yes', True), ('on', True),
            ('false', False), ('0', False), ('no', False), ('off', False),
        ):
            with self.subTest(tls=value):
                self.assertEqual(
                    self.load_production_settings({'EMAIL_USE_TLS': value}).EMAIL_USE_TLS,
                    expected,
                )
        for value in ('invalid', 'maybe'):
            with self.subTest(boolean=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'EMAIL_USE_TLS': value})
        with self.assertRaises(ImproperlyConfigured):
            self.load_production_settings({'EMAIL_USE_TLS': 'true', 'EMAIL_USE_SSL': 'true'})

        production = self.load_production_settings()
        self.assertTrue(production.EMAIL_USE_TLS)
        self.assertFalse(production.EMAIL_USE_SSL)
        self.assertEqual(production.EMAIL_TIMEOUT, 10)
        self.assertEqual(production.SERVER_EMAIL, production.DEFAULT_FROM_EMAIL)
        self.assertEqual(production.EMAIL_SUBJECT_PREFIX, '[InkSpire]')
        for value in ('0', '-1', 'invalid'):
            with self.subTest(timeout=value), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({'EMAIL_TIMEOUT': value})
        for name in ('DEFAULT_FROM_EMAIL', 'SERVER_EMAIL'):
            with self.subTest(address=name), self.assertRaises(ImproperlyConfigured):
                self.load_production_settings({name: 'not-an-email'})

    def test_entry_points_default_to_production_and_manage_defaults_to_development(self):
        project_root = Path(__file__).resolve().parent.parent
        for filename in ('wsgi.py', 'asgi.py'):
            with self.subTest(filename=filename):
                source = (project_root / 'blog_main' / filename).read_text()
                self.assertIn(
                    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_main.settings_prod')",
                    source,
                )
        manage_source = (project_root / 'manage.py').read_text()
        self.assertIn(
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_main.settings')",
            manage_source,
        )


class ProfileAndGoogleOAuthTests(TestCase):
    """Profile management + Google OAuth wiring: set-password flow for
    social-only accounts, profile UI branching, connected-accounts display,
    and the allauth sign-up signal that provisions a profile."""

    def setUp(self):
        self.password_user = User.objects.create_user(
            username='has-pw', email='haspw@example.com', password='test-password'
        )
        UserProfile.objects.create(user=self.password_user)

        self.social_user = User.objects.create_user(
            username='googler', email='googler@example.com'
        )
        self.social_user.set_unusable_password()
        self.social_user.save()
        UserProfile.objects.create(user=self.social_user)

    # ---- set-password / change-password routing --------------------------
    def test_social_only_user_can_set_password(self):
        self.client.force_login(self.social_user)
        get_response = self.client.get(reverse('set_password'))
        self.assertEqual(get_response.status_code, 200)

        response = self.client.post(
            reverse('set_password'),
            {'new_password1': 'Str0ng-Pass!23', 'new_password2': 'Str0ng-Pass!23'},
        )
        self.assertRedirects(response, reverse('profile'))
        self.social_user.refresh_from_db()
        self.assertTrue(self.social_user.has_usable_password())

    def test_change_password_redirects_social_only_user_to_set_password(self):
        self.client.force_login(self.social_user)
        response = self.client.get(reverse('change_password'))
        self.assertRedirects(response, reverse('set_password'))

    def test_set_password_redirects_user_who_already_has_one(self):
        self.client.force_login(self.password_user)
        response = self.client.get(reverse('set_password'))
        self.assertRedirects(response, reverse('change_password'))

    # ---- profile page UI branching ---------------------------------------
    def test_profile_offers_set_password_for_social_only_user(self):
        self.client.force_login(self.social_user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('set_password'))
        self.assertNotContains(response, reverse('change_password'))

    def test_profile_offers_change_password_for_password_user(self):
        self.client.force_login(self.password_user)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, reverse('change_password'))

    def test_edit_profile_page_renders(self):
        self.client.force_login(self.password_user)
        response = self.client.get(reverse('edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit profile')
        # Uses the external, CSP-safe avatar-preview script (no inline script).
        self.assertContains(response, 'js/avatar-preview.js')

    def test_profile_shows_connect_google_when_not_connected(self):
        self.client.force_login(self.password_user)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'Connect Google')

    def test_profile_shows_disconnect_when_google_connected(self):
        from allauth.socialaccount.models import SocialAccount
        SocialAccount.objects.create(
            user=self.password_user, provider='google', uid='g-123',
            extra_data={'email': 'haspw@example.com'},
        )
        self.client.force_login(self.password_user)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'Disconnect')
        self.assertContains(response, 'Connected')

    # ---- allauth sign-up signal ------------------------------------------
    def test_signup_signal_creates_profile_and_imports_google_name(self):
        from types import SimpleNamespace
        from allauth.account.signals import user_signed_up

        new_user = User.objects.create_user(username='grace')
        new_user.set_unusable_password()
        new_user.save()
        self.assertFalse(UserProfile.objects.filter(user=new_user).exists())

        sociallogin = SimpleNamespace(
            account=SimpleNamespace(
                extra_data={'given_name': 'Grace', 'family_name': 'Hopper'}
            )
        )
        user_signed_up.send(
            sender=User, request=None, user=new_user, sociallogin=sociallogin
        )

        self.assertTrue(UserProfile.objects.filter(user=new_user).exists())
        new_user.refresh_from_db()
        self.assertEqual(new_user.first_name, 'Grace')
        self.assertEqual(new_user.last_name, 'Hopper')

    def test_signup_signal_is_idempotent_for_existing_profile(self):
        from allauth.account.signals import user_signed_up

        # password_user already has a profile from setUp; the signal must not
        # raise (get_or_create) when fired for a non-social sign-up.
        user_signed_up.send(
            sender=User, request=None, user=self.password_user, sociallogin=None
        )
        self.assertEqual(
            UserProfile.objects.filter(user=self.password_user).count(), 1
        )
