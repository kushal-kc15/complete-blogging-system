
import time
from django.shortcuts import render, redirect, get_object_or_404
from blogs.models import Blog, Category
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
    post=get_object_or_404(Blog, id=id)
    form=BlogForm(instance=post)
    if request.method=='POST':
        form=BlogForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post=form.save()
            title=form.cleaned_data['title']
            post.slug=slugify(title)+'-'+ str(int(time.time()))
            post.save()
            return redirect('posts')
        else:
            print(form.errors)
    else:
        form=BlogForm(instance=post)
    context={
        'form':form,
    }
    return render(request, 'dashboard/edit_post.html', context)

def delete_post(request, id):
    post=get_object_or_404(Blog, id=id)
    post.delete()
    return redirect('posts')