from django.contrib.auth.models import User
from .forms import AddUserForm, EditUserForm
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from blogs.models import Blog, Category, Comment, Contact, Series
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.views.decorators.http import require_POST
from .forms import CategoryForm, BlogForm
# Create your views here.


def is_dashboard_admin(user):
    """A dashboard admin sees the whole site (all authors' content).

    Everyone else who reaches the dashboard is an author and sees only their
    own posts and stats (the modern per-author dashboard model).
    """
    return user.is_staff or user.is_superuser


def can_access_dashboard(user):
    """Any authenticated user can access the dashboard to write posts."""
    return user.is_authenticated


def superuser_required(view_func):
    return user_passes_test(
        lambda user: user.is_superuser,
        login_url='login',
        redirect_field_name=None,
    )(view_func)


def comment_moderator_required(view_func):
    return user_passes_test(
        lambda user: user.is_staff or user.has_perm('blogs.view_comment') or user.has_perm('blogs.change_comment'),
        login_url='login',
        redirect_field_name=None,
    )(view_func)


def comment_change_required(view_func):
    return user_passes_test(
        lambda user: user.is_staff or user.has_perm('blogs.change_comment'),
        login_url='login',
        redirect_field_name=None,
    )(view_func)


@login_required(login_url='login')
@user_passes_test(
    can_access_dashboard,
    login_url='login',
    redirect_field_name=None,
)
def dashboard(request):
    return redirect('my_stories')


@login_required(login_url='login')
@permission_required('blogs.view_category', raise_exception=True)
def categories(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'dashboard/categories.html', context)


@login_required(login_url='login')
@permission_required('blogs.add_category', raise_exception=True)
def add_category(request):
    # form = CategoryForm()
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('categories')
    else:
        form = CategoryForm()
    context = {
        'form': form
    }
    return render(request, 'dashboard/add_category.html', context)


@login_required(login_url='login')
@permission_required('blogs.change_category', raise_exception=True)
def edit_category(request, id):
    category = get_object_or_404(Category, id=id)
    form = CategoryForm(instance=category)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('categories')
    context = {
        'form': form,
        'category': category,
    }
    return render(request, 'dashboard/edit_category.html', context)


@login_required(login_url='login')
@permission_required('blogs.delete_category', raise_exception=True)
@require_POST
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    try:
        category.delete()
    except ProtectedError:
        messages.error(
            request,
            'This category cannot be deleted because it is being used by one or more posts.',
        )
    return redirect('categories')


@login_required(login_url='login')
def posts(request):
    is_admin = is_dashboard_admin(request.user)
    post_list = Blog.objects.select_related('category', 'author').order_by('-updated_at')
    # Authors only manage their own posts; admins manage every author's posts.
    if not is_admin:
        post_list = post_list.filter(author=request.user)
    paginator = Paginator(post_list, 6)
    posts = paginator.get_page(request.GET.get('page'))
    context = {
        'is_dashboard_admin': is_admin,
        'posts': posts,
    }
    return render(request, 'dashboard/posts.html', context)


@login_required(login_url='login')
def add_post(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            title = form.cleaned_data['title']
            for _ in range(5):
                post.slug = Blog.generate_unique_slug(title)
                try:
                    post.save()
                except IntegrityError:
                    if Blog.objects.filter(slug=post.slug).exists():
                        continue
                    raise
                return redirect('my_stories')
            form.add_error(None, 'Unable to create a unique post URL. Please try again.')
    else:
        form = BlogForm(user=request.user)
    context = {
        'form': form
    }
    return render(request, 'dashboard/add_post.html', context)


@login_required(login_url='login')
def edit_post(request, id):
    post = get_object_or_404(Blog, id=id)
    # Authors may only edit their own posts; admins may edit any post.
    if not is_dashboard_admin(request.user) and post.author_id != request.user.id:
        raise Http404
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=post, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('my_stories')
    else:
        form = BlogForm(instance=post, user=request.user)
    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'dashboard/edit_post.html', context)


@login_required(login_url='login')
@require_POST
def delete_post(request, id):
    post = get_object_or_404(Blog, id=id)
    # Authors may only delete their own posts; admins may delete any post.
    if not is_dashboard_admin(request.user) and post.author_id != request.user.id:
        raise Http404
    post.delete()
    return redirect('my_stories')


@login_required(login_url='login')
@comment_moderator_required
def comments(request):
    comment_list = Comment.objects.select_related(
        'user', 'blog', 'blog__category'
    ).order_by('-created_at')
    paginator = Paginator(comment_list, 10)
    comments = paginator.get_page(request.GET.get('page'))
    context = {
        'comments': comments,
        'visible_count': Comment.objects.filter(is_visible=True).count(),
        'hidden_count': Comment.objects.filter(is_visible=False).count(),
    }
    return render(request, 'dashboard/comments.html', context)


@login_required(login_url='login')
@comment_change_required
@require_POST
def toggle_comment_visibility(request, id):
    comment = get_object_or_404(Comment, id=id)
    comment.is_visible = not comment.is_visible
    comment.save(update_fields=['is_visible', 'updated_at'])
    action = 'visible' if comment.is_visible else 'hidden'
    messages.success(request, f'Comment marked as {action}.')
    return redirect('dashboard_comments')


@login_required(login_url='login')
@superuser_required
def users(request):
    user_list = User.objects.all().order_by('id')
    paginator = Paginator(user_list, 10)
    users = paginator.get_page(request.GET.get('page'))
    context = {
        'users': users,
    }
    return render(request, 'dashboard/users.html', context)


@login_required(login_url='login')
@superuser_required
def add_user(request):
    if request.method == 'POST':
        form = AddUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('users')
    else:
        form = AddUserForm()
    context = {
        'form': form,
    }
    return render(request, 'dashboard/add_user.html', context)


@login_required(login_url='login')
@superuser_required
def edit_user(request, id):
    user = get_object_or_404(User, id=id)
    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users')
    else:
        form = EditUserForm(instance=user)
    context = {
        'form': form,
        'edit_user': user,
    }
    return render(request, 'dashboard/edit_user.html', context)


@login_required(login_url='login')
@superuser_required
@require_POST
def delete_user(request, id):
    user = get_object_or_404(User, id=id)
    try:
        user.delete()
    except ProtectedError:
        messages.error(
            request,
            'This user cannot be deleted because they are the author of one or more posts.',
        )
    return redirect('users')


# ======== Contact Messages Management ========
@login_required
@permission_required('blogs.view_contact', raise_exception=True)
def contact_messages(request):
    message_list = Contact.objects.all().order_by('-created_at')
    paginator = Paginator(message_list, 10)
    messages = paginator.get_page(request.GET.get('page'))
    unread_count = Contact.objects.filter(is_read=False).count()
    context = {
        'messages': messages,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard/messages.html', context)


@login_required
@permission_required('blogs.view_contact', raise_exception=True)
def view_message(request, id):
    message = get_object_or_404(Contact, id=id)
    context = {
        'message': message,
    }
    return render(request, 'dashboard/view_message.html', context)


@login_required
@permission_required('blogs.view_contact', raise_exception=True)
@require_POST
def mark_message_read(request, id):
    message = get_object_or_404(Contact, id=id)
    if not message.is_read:
        message.is_read = True
        message.save(update_fields=['is_read'])
    messages.success(request, 'Message marked as read.')
    return redirect('view_message', id=message.id)


@login_required
@permission_required('blogs.delete_contact', raise_exception=True)
@require_POST
def delete_message(request, id):
    message = get_object_or_404(Contact, id=id)
    message.delete()
    return redirect('contact_messages')


# ======== Series Management ========
@login_required(login_url='login')
def series_list(request):
    user_series = Series.objects.filter(author=request.user).order_by('-created_at')
    context = {'series_list': user_series}
    return render(request, 'dashboard/series.html', context)


@login_required(login_url='login')
def add_series(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            Series.objects.create(name=name, description=description, author=request.user)
            return redirect('series_list')
        else:
            messages.error(request, 'Series name is required.')
    return render(request, 'dashboard/add_series.html')


@login_required(login_url='login')
def edit_series(request, id):
    series = get_object_or_404(Series, id=id, author=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            series.name = name
            series.description = description
            series.save()
            return redirect('series_list')
        else:
            messages.error(request, 'Series name is required.')
    context = {'series': series}
    return render(request, 'dashboard/edit_series.html', context)


@login_required(login_url='login')
@require_POST
def delete_series(request, id):
    series = get_object_or_404(Series, id=id, author=request.user)
    series.delete()
    return redirect('series_list')
