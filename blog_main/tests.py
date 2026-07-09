from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blogs.models import Blog, Category


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
