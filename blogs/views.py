from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.models import User
from .models import Blog, Category, Comment, Like, Bookmark, Contact, UserProfile, Follow
from django.db import IntegrityError
from django.db.models import Count, F, Q
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django_ratelimit.core import get_usage
from math import ceil
from .forms import CommentForm, ContactForm


# Create your views here.


def _rate_limit_usage(request, *, group, key, rate):
    return get_usage(
        request,
        group=group,
        key=key,
        rate=rate,
        method=('POST',),
        increment=True,
    )


def _add_retry_after(response, usage):
    time_left = usage.get('time_left') if usage else None
    if time_left and time_left > 0:
        response['Retry-After'] = str(max(1, ceil(time_left)))
    return response


def Posts_by_category(request, category_id):
    # fetch the post that belongs to the category with the id category_id.
    # partials/post_card.html renders post.author.username and post.category
    # for every post in the list, so select_related avoids a query per post
    # per relation instead of a query per row.
    posts_list = Blog.objects.published().filter(
        category=category_id
    ).select_related('author', 'category').order_by('-created_at')
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


def category_index(request):
    # Every category, alphabetically, each annotated with a count of its
    # published posts. The filtered Count only counts related Blog rows
    # with status='published', so draft posts never inflate a category's
    # displayed count. No select_related/prefetch_related is needed here:
    # the template only renders each category's own fields (name) plus the
    # annotated count, with no other related object accessed per row.
    categories = Category.objects.annotate(
        published_post_count=Count(
            'blog', filter=Q(blog__status='published')
        )
    ).order_by('name')

    context = {
        'categories': categories,
    }
    return render(request, 'categories.html', context)


def BlogDetail(request, slug):
    # The template renders post.author and post.category (name, id, url)
    # directly, so select_related avoids a separate query for each.
    post = get_object_or_404(
        Blog.objects.select_related('author', 'category'), slug=slug
    )
    # A post is publicly visible only when it is published AND its
    # publication time is either unset or has already passed. A published
    # post with a future published_at is a Scheduled_Blog and must be treated
    # as a preview (hidden from the public) until its time arrives.
    now = timezone.now()
    is_public = post.status == 'published' and (
        post.published_at is None or post.published_at <= now
    )
    is_preview = not is_public
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

    # Get comments (only parent comments, replies are fetched via related_name).
    # The template renders comment.user.username and reply.user.username for
    # every comment and reply, so select_related('user') on both querysets
    # avoids a query per comment/reply. Replies are still fetched in a single
    # extra query via prefetch_related rather than per-parent-comment queries.
    visible_replies = Comment.objects.filter(
        is_visible=True
    ).select_related('user').order_by('created_at')
    comments = Comment.objects.filter(
        blog=post, parent=None, is_visible=True
    ).select_related('user').prefetch_related(
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

    # Related posts (same category, excluding current post). The related
    # card only renders fields on the post itself today, but select_related
    # keeps this queryset consistent with other post listings and avoids a
    # query per related post if the card ever renders author/category.
    related_posts = Blog.objects.published().filter(
        category=post.category
    ).exclude(id=post.id).select_related(
        'author', 'category'
    ).order_by('-created_at')[:3]

    comment_form = CommentForm()
    rate_limited = False
    rate_limit_usage = None
    if request.method == 'POST' and not is_preview:
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")

        comment_form = CommentForm(request.POST)
        rate_limit_usage = _rate_limit_usage(
            request,
            group='comment-submit',
            key='user',
            rate=settings.COMMENT_RATE_LIMIT,
        )
        if rate_limit_usage and rate_limit_usage['should_limit']:
            comment_form.add_error(
                None, 'Too many comment submissions. Please try again shortly.'
            )
            rate_limited = True
        elif comment_form.is_valid():
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
    response = render(
        request, 'blog_detail.html', context, status=429 if rate_limited else 200
    )
    if rate_limited:
        return _add_retry_after(response, rate_limit_usage)
    return response


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
@require_POST
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        return redirect('Blog_detail', slug=comment.blog.slug)

    comment_form = CommentForm(request.POST, instance=comment)
    if comment_form.is_valid():
        comment_form.save()
    else:
        for error in comment_form.errors.get('comment', []):
            messages.error(request, error)
        for error in comment_form.non_field_errors():
            messages.error(request, error)
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
        rate_limit_usage = _rate_limit_usage(
            request,
            group='contact-submit',
            key='ip',
            rate=settings.CONTACT_RATE_LIMIT,
        )
        if rate_limit_usage and rate_limit_usage['should_limit']:
            form.add_error(
                None, 'Too many contact submissions. Please try again shortly.'
            )
            response = render(request, 'contact.html', {'form': form}, status=429)
            return _add_retry_after(response, rate_limit_usage)
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


@login_required(login_url='login')
@require_POST
def follow_author(request, username):
    author = get_object_or_404(User, username=username)
    # Guard self-follow: creating a Follow from a user to themselves is
    # rejected (Requirement 6.3). Silently no-op back to the profile.
    if author.id != request.user.id:
        # get_or_create makes the follow idempotent: submitting the control
        # more than once yields exactly one Follow record (Requirement 7.3).
        # A concurrent duplicate that slips past get_or_create trips the DB
        # UniqueConstraint; catch the IntegrityError and treat it as a no-op.
        try:
            Follow.objects.get_or_create(
                follower=request.user, followed=author
            )
        except IntegrityError:
            pass
    return redirect('author_profile', username=author.username)


@login_required(login_url='login')
@require_POST
def unfollow_author(request, username):
    author = get_object_or_404(User, username=username)
    # Deleting is a no-op when no Follow record exists; either way the
    # relationship ends up unfollowed (Requirement 7.4).
    Follow.objects.filter(follower=request.user, followed=author).delete()
    return redirect('author_profile', username=author.username)
