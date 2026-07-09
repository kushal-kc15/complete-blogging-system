from .models import Category,Blog
def get_categories(request):
  categories=Category.objects.all()
  return dict(categories=categories)

def get_posts(request):
  posts=Blog.objects.published()
  return dict(posts=posts)
