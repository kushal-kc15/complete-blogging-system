from .models import Category
def get_categories(request):
  categories=Category.objects.all()
  return dict(categories=categories)

def get_posts(request):
  posts=Blog.objects.all()
  return dict(posts=posts)