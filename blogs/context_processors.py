from django.core.cache import cache

from .models import Category, Blog

GLOBAL_CATEGORIES_CACHE_KEY = 'global_categories'
GLOBAL_CATEGORIES_CACHE_TIMEOUT = 60 * 10  # 10 minutes


def get_categories(request):
    categories = cache.get(GLOBAL_CATEGORIES_CACHE_KEY)
    if categories is None:
        categories = list(Category.objects.order_by('name'))
        cache.set(
            GLOBAL_CATEGORIES_CACHE_KEY,
            categories,
            GLOBAL_CATEGORIES_CACHE_TIMEOUT,
        )
    return dict(categories=categories)


def get_posts(request):
    posts = Blog.objects.published()
    return dict(posts=posts)
