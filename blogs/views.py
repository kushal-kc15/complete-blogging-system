from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from .models import Blog, Category, Comment, Like, Bookmark, Contact, UserProfile
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST


# Create your views here.


def Posts_by_category(request, category_id):
    # fetch the post that belongs to the category with the id category_id
    posts_list = Blog.objects.filter(
        status="published", category=category_id).order_by('-created_at')
    category = get_object_or_404(Category, id=category_id)

    # Pagination
    paginator = Paginator(posts_list, 6)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    context = {
        'posts': posts,
        'category': category,
    }
    return render(request, 'posts_by_category.html', context)


def BlogDetail(request, slug):
    post = get_object_or_404(Blog, slug=slug, status="published")

    # Increment view count
    post.views += 1
    post.save(update_fields=['views'])

    # Get comments (only parent comments, replies are fetched via related_name)
    comments = Comment.objects.filter(
        blog=post, parent=None).order_by('-created_at')
    comment_count = Comment.objects.filter(blog=post).count()

    # Check if user has liked/bookmarked
    user_has_liked = False
    user_has_bookmarked = False
    if request.user.is_authenticated:
        user_has_liked = Like.objects.filter(
            user=request.user, blog=post).exists()
        user_has_bookmarked = Bookmark.objects.filter(
            user=request.user, blog=post).exists()

    # Related posts (same category, excluding current post)
    related_posts = Blog.objects.filter(
        category=post.category,
        status="published"
    ).exclude(id=post.id).order_by('-created_at')[:3]

    # Handle comment submission
    if request.method == 'POST':
        if request.user.is_authenticated:
            comment_text = request.POST.get('comment')
            parent_id = request.POST.get('parent_id')
            if comment_text:
                parent = None
                if parent_id:
                    parent = Comment.objects.filter(
                        id=parent_id, blog=post
                    ).first()
                    if parent is None:
                        messages.error(
                            request,
                            'The comment you tried to reply to is not valid.'
                        )
                        return redirect('Blog_detail', slug=slug)
                Comment.objects.create(
                    user=request.user,
                    blog=post,
                    parent=parent,
                    comment=comment_text
                )
                return redirect('Blog_detail', slug=slug)

    context = {
        'post': post,
        'comments': comments,
        'comment_count': comment_count,
        'related_posts': related_posts,
        'user_has_liked': user_has_liked,
        'user_has_bookmarked': user_has_bookmarked,
        'like_count': post.likes.count(),
    }
    return render(request, 'blog_detail.html', context)


@login_required(login_url='login')
@require_POST
def like_post(request, slug):
    post = get_object_or_404(Blog, slug=slug)
    like, created = Like.objects.get_or_create(user=request.user, blog=post)
    if not created:
        like.delete()
    return redirect('Blog_detail', slug=slug)


@login_required(login_url='login')
@require_POST
def bookmark_post(request, slug):
    post = get_object_or_404(Blog, slug=slug)
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user, blog=post)
    if not created:
        bookmark.delete()
    return redirect('Blog_detail', slug=slug)


@login_required(login_url='login')
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        return redirect('Blog_detail', slug=comment.blog.slug)

    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            comment.comment = comment_text
            comment.save()
    return redirect('Blog_detail', slug=comment.blog.slug)


@login_required(login_url='login')
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    slug = comment.blog.slug
    if comment.user == request.user:
        comment.delete()
    return redirect('Blog_detail', slug=slug)


@login_required(login_url='login')
def my_bookmarks(request):
    bookmarks = Bookmark.objects.filter(
        user=request.user).order_by('-created_at')
    context = {
        'bookmarks': bookmarks,
    }
    return render(request, 'my_bookmarks.html', context)


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        if name and email and subject and message:
            Contact.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            return render(request, 'contact.html', {'success': True})
    return render(request, 'contact.html')


def Search(request):
    keyword = request.GET.get('keyword')
    posts_list = Blog.objects.filter(
        Q(title__icontains=keyword) |
        Q(short_description__icontains=keyword) |
        Q(blog_body__icontains=keyword),
        status="published"
    ).order_by('-created_at')

    paginator = Paginator(posts_list, 6)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    context = {
        'posts': posts,
        'keyword': keyword,
    }
    return render(request, 'search.html', context)


def AuthorProfile(request, username):
    author = get_object_or_404(User, username=username)
    profile = UserProfile.objects.filter(user=author).first()
    posts_list = Blog.objects.filter(
        author=author,
        status='published',
    ).select_related('category', 'author').order_by('-created_at')

    paginator = Paginator(posts_list, 6)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    context = {
        'author_profile_user': author,
        'author_profile': profile,
        'posts': posts,
    }
    return render(request, 'author_profile.html', context)
