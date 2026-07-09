from django.contrib.auth.models import User
from .forms import AddUserForm, EditUserForm
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from blogs.models import Blog, Category, Comment, Contact
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.views.decorators.http import require_POST
from .forms import CategoryForm, BlogForm
from django.template.defaultfilters import slugify
# Create your views here.


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
    lambda user: user.is_staff or user.has_perms([
        'blogs.view_blog', 'blogs.view_category',
    ]),
    login_url='login',
    redirect_field_name=None,
)
def dashboard(request):
    blogs_count = Blog.objects.all().count()
    category_count = Category.objects.all().count()
    published_count = Blog.objects.filter(status='published').count()
    draft_count = Blog.objects.filter(status='draft').count()
    featured_count = Blog.objects.filter(is_featured=True).count()
    recent_posts = Blog.objects.select_related(
        'category', 'author'
    ).order_by('-updated_at')[:5]
    context = {
        'blogs_count': blogs_count,
        'category_count': category_count,
        'published_count': published_count,
        'draft_count': draft_count,
        'featured_count': featured_count,
        'recent_posts': recent_posts,
    }
    return render(request, 'dashboard/dashboard.html', context)


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
    category.delete()
    return redirect('categories')


@login_required(login_url='login')
@permission_required('blogs.view_blog', raise_exception=True)
def posts(request):
    posts = Blog.objects.select_related('category', 'author').order_by('-updated_at')
    context = {
        'posts': posts
    }
    return render(request, 'dashboard/posts.html', context)


@login_required(login_url='login')
@permission_required('blogs.add_blog', raise_exception=True)
def add_post(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            title = form.cleaned_data['title']
            # Create a unique slug using title and timestamp
            import time
            post.slug = slugify(title) + '-' + str(int(time.time()))
            post.save()
            return redirect('posts')
        else:
            print(form.errors)
    else:
        form = BlogForm()
    context = {
        'form': form
    }
    return render(request, 'dashboard/add_post.html', context)


@login_required(login_url='login')
@permission_required('blogs.change_blog', raise_exception=True)
def edit_post(request, id):
    post = get_object_or_404(Blog, id=id)
    form = BlogForm(instance=post)
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            title = form.cleaned_data['title']
            post.slug = slugify(title)+'-' + str(int(time.time()))
            post.save()
            return redirect('posts')
        else:
            print(form.errors)
    else:
        form = BlogForm(instance=post)
    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'dashboard/edit_post.html', context)


@login_required(login_url='login')
@permission_required('blogs.delete_blog', raise_exception=True)
@require_POST
def delete_post(request, id):
    post = get_object_or_404(Blog, id=id)
    post.delete()
    return redirect('posts')


@login_required(login_url='login')
@comment_moderator_required
def comments(request):
    comments = Comment.objects.select_related(
        'user', 'blog', 'blog__category'
    ).order_by('-created_at')
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
    users = User.objects.all()
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
    user.delete()
    return redirect('users')


# ======== Contact Messages Management ========
@login_required
@permission_required('blogs.view_contact', raise_exception=True)
def contact_messages(request):
    messages = Contact.objects.all().order_by('-created_at')
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
    # Mark as read when viewed
    if not message.is_read:
        message.is_read = True
        message.save()
    context = {
        'message': message,
    }
    return render(request, 'dashboard/view_message.html', context)


@login_required
@permission_required('blogs.delete_contact', raise_exception=True)
@require_POST
def delete_message(request, id):
    message = get_object_or_404(Contact, id=id)
    message.delete()
    return redirect('contact_messages')
