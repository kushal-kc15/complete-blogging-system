from django.core.cache import cache

from .models import Category, Blog, Bookmark

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


def get_user_bookmarks(request):
    if request.user.is_authenticated:
        slugs = set(
            Bookmark.objects.filter(user=request.user)
            .values_list('blog__slug', flat=True)
        )
        return {'user_bookmarked_slugs': slugs}
    return {'user_bookmarked_slugs': set()}
