import importlib
import os
import sys
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from PIL import Image
from unittest.mock import patch

from blogs.forms import ContactForm
from blogs.models import Blog, Category, Contact, UserProfile
from .feeds import LatestPostsFeed


class Custom404Tests(TestCase):
    @override_settings(DEBUG=False)
    def test_custom_404_page_uses_readable_navigation_text(self):
        response = self.client.get('/route-that-does-not-exist-404/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Go back home', status_code=404)
        self.assertNotContains(response, 'youâ€™re', status_code=404)


class ContactRouteTests(TestCase):
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
