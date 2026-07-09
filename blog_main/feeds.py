from django.contrib.syndication.views import Feed
from django.urls import reverse
from blogs.models import Blog


class LatestPostsFeed(Feed):
    title = "InkSpire - Latest Posts"
    link = "/"
    description = "Latest posts from InkSpire blogging platform"

    def items(self):
        return Blog.objects.published().order_by('-created_at')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.short_description

    def item_link(self, item):
        return reverse('Blog_detail', args=[item.slug])

    def item_pubdate(self, item):
        return item.created_at

    def item_author_name(self, item):
        return item.author.get_full_name() or item.author.username
