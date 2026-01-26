from django.shortcuts import render,get_object_or_404,redirect
from django.http import HttpResponse
from .models import Blog, Category
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