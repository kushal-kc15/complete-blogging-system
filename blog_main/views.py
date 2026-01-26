from django.shortcuts import render
from blogs.models import Category,Blog
# from django.http import HttpResponse
def home(request):
    featured_post=Blog.objects.filter(is_featured=True).order_by('updated_at')
    posts=Blog.objects.filter(is_featured=False,status='published').order_by('-updated_at')
    context={
        'featured_post':featured_post,
        'posts':posts,
        }
    return render(request, "home.html",context)

def about(request):
    return render(request, 'about.html')
