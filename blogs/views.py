from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib.auth.models import User
from .models import Blog, Category, Comment, Like, Bookmark, Contact, UserProfile
from django.db.models import F, Q
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from .forms import CommentForm, ContactForm


# Create your views here.


def Posts_by_category(request, category_id):
    # fetch the post that belongs to the category with the id category_id
    posts_list = Blog.objects.published().filter(
        category=category_id).order_by('-created_at')
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
    post = get_object_or_404(Blog, slug=slug)
    is_preview = post.status != 'published'
    can_preview = (
        request.user.is_authenticated and (
            post.author_id == request.user.id or
            request.user.is_staff or
            request.user.has_perm('blogs.change_blog')
        )
    )
    if is_preview and not can_preview:
        raise Http404

    # Increment view count
    if not is_preview:
        Blog.objects.filter(pk=post.pk).update(views=F('views') + 1)
        post.refresh_from_db(fields=['views'])

    # Get comments (only parent comments, replies are fetched via related_name)
    visible_replies = Comment.objects.filter(is_visible=True).order_by('created_at')
    comments = Comment.objects.filter(
        blog=post, parent=None, is_visible=True
    ).prefetch_related(
        Prefetch('replies', queryset=visible_replies, to_attr='visible_replies')
    ).order_by('-created_at')
    comment_count = Comment.objects.filter(
        blog=post, is_visible=True
    ).filter(Q(parent__isnull=True) | Q(parent__is_visible=True)).count()

    # Check if user has liked/bookmarked
    user_has_liked = False
    user_has_bookmarked = False
    if request.user.is_authenticated:
        user_has_liked = Like.objects.filter(
            user=request.user, blog=post).exists()
        user_has_bookmarked = Bookmark.objects.filter(
            user=request.user, blog=post).exists()

    # Related posts (same category, excluding current post)
    related_posts = Blog.objects.published().filter(
        category=post.category
    ).exclude(id=post.id).order_by('-created_at')[:3]

    comment_form = CommentForm()
    if request.method == 'POST' and not is_preview:
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            parent = None
            parent_id = (request.POST.get('parent_id') or '').strip()
            if parent_id:
                try:
                    parent_id = int(parent_id)
                except ValueError:
                    parent = None
                else:
                    parent = Comment.objects.filter(
                        id=parent_id, blog=post, is_visible=True
                    ).first()
                if parent is None:
                    comment_form.add_error(
                        None, 'The comment you tried to reply to is not valid.'
                    )
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.blog = post
                comment.parent = parent
                comment.save()
                return redirect('Blog_detail', slug=slug)

    context = {
        'post': post,
        'comments': comments,
        'comment_count': comment_count,
        'related_posts': related_posts,
        'user_has_liked': user_has_liked,
        'user_has_bookmarked': user_has_bookmarked,
        'like_count': post.likes.count(),
        'is_preview': is_preview,
        'comment_form': comment_form,
    }
    return render(request, 'blog_detail.html', context)


@login_required(login_url='login')
@require_POST
def like_post(request, slug):
    post = get_object_or_404(Blog.objects.published(), slug=slug)
    like, created = Like.objects.get_or_create(user=request.user, blog=post)
    if not created:
        like.delete()
    return redirect('Blog_detail', slug=slug)


@login_required(login_url='login')
@require_POST
def bookmark_post(request, slug):
    post = get_object_or_404(Blog.objects.published(), slug=slug)
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
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Thank you for your message! We'll get back to you soon."
            )
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


def Search(request):
    keyword = (request.GET.get('keyword') or '').strip()
    if keyword:
        posts_list = Blog.objects.published().filter(
            Q(title__icontains=keyword) |
            Q(short_description__icontains=keyword) |
            Q(blog_body__icontains=keyword)
        ).order_by('-created_at')
    else:
        posts_list = Blog.objects.published().none()

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
    posts_list = Blog.objects.published().filter(
        author=author,
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
