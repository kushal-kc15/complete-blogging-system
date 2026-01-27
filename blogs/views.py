from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Blog, Category, Comment
from django.db.models import Q
# Create your views here.


def Posts_by_category(request, category_id):
    # fetch the post that belongs to the category with the id category_id
    posts = Blog.objects.filter(status="published", category=category_id)
    category = get_object_or_404(Category, id=category_id)
    context = {
        'posts': posts,
        'category': category,
    }
    return render(request, 'posts_by_category.html', context)


def BlogDetail(request, slug):
    post = get_object_or_404(Blog, slug=slug, status="published")
    comments = Comment.objects.filter(blog=post).order_by('-created_at')
    comment_count = comments.count()

    if request.method == 'POST':
        if request.user.is_authenticated:
            comment_text = request.POST.get('comment')
            if comment_text:
                Comment.objects.create(
                    user=request.user,
                    blog=post,
                    Comment=comment_text
                )
                return redirect('Blog_detail', slug=slug)

    context = {
        'post': post,
        'comments': comments,
        'comment_count': comment_count,
    }
    return render(request, 'blog_detail.html', context)


def Search(request):
    keyword = request.GET.get('keyword')
    posts = Blog.objects.filter(Q(title__icontains=keyword) | Q(
        short_description__icontains=keyword) | Q(blog_body__icontains=keyword), status="published")
    context = {
        'posts': posts,
        'keyword': keyword,
    }
    return render(request, 'search.html', context)
