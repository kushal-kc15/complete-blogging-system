from django.shortcuts import render,get_object_or_404,redirect
from django.http import HttpResponse
from .models import Blog, Category
from django.db.models import Q
# Create your views here.
def Posts_by_category(request,category_id):
  # fetch the post that belongs to the category with the id category_id 
  posts=Blog.objects.filter(status="published",category=category_id)
  category=get_object_or_404(Category,id=category_id) 
  context={
    'posts':posts,
    'category':category,
  }
  return render(request,'posts_by_category.html',context)

def BlogDetail(request,slug):
  post=get_object_or_404(Blog,slug=slug,status="published")
  context={
    'post':post,
  }
  return render(request,'blog_detail.html',context)

def Search(request):
  keyword=request.GET.get('keyword')
  posts=Blog.objects.filter(Q(title__icontains=keyword)|Q(short_description__icontains=keyword) | Q(blog_body__icontains=keyword), status="published")
  context={
    'posts':posts,
    'keyword':keyword,
  }
  return render(request,'search.html',context)