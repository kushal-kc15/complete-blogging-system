from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blogs.models import Blog


class BlogSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Blog.objects.published().order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('Blog_detail', args=[obj.slug])


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return ['home', 'about', 'contact']

    def location(self, item):
        return reverse(item)
