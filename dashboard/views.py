from django.contrib.auth.models import User
from .forms import AddUserForm, EditUserForm
import time
from django.shortcuts import render, redirect, get_object_or_404
from blogs.models import Blog, Category, Contact
from django.contrib.auth.decorators import login_required
from .forms import CategoryForm, BlogForm
from django.template.defaultfilters import slugify
# Create your views here.


@login_required(login_url='login')
def dashboard(request):
    blogs_count = Blog.objects.all().count()
    category_count = Category.objects.all().count()
    context = {
        'blogs_count': blogs_count,
        'category_count': category_count,
    }
    return render(request, 'dashboard/dashboard.html', context)


def categories(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'dashboard/categories.html', context)


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


def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    category.delete()
    return redirect('categories')


def posts(request):
    posts = Blog.objects.all()
    context = {
        'posts': posts
    }
    return render(request, 'dashboard/posts.html', context)


@login_required(login_url='login')
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
    }
    return render(request, 'dashboard/edit_post.html', context)


def delete_post(request, id):
    post = get_object_or_404(Blog, id=id)
    post.delete()
    return redirect('posts')


def users(request):
    users = User.objects.all()
    context = {
        'users': users,
    }
    return render(request, 'dashboard/users.html', context)


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


def delete_user(request, id):
    user = get_object_or_404(User, id=id)
    user.delete()
    return redirect('users')


# ======== Contact Messages Management ========
@login_required
def contact_messages(request):
    messages = Contact.objects.all().order_by('-created_at')
    unread_count = Contact.objects.filter(is_read=False).count()
    context = {
        'messages': messages,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard/messages.html', context)


@login_required
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
def delete_message(request, id):
    message = get_object_or_404(Contact, id=id)
    message.delete()
    return redirect('contact_messages')
