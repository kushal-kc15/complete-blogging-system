from django.shortcuts import render,redirect,get_object_or_404
from blogs.models import Blog, Category
from django.contrib.auth.decorators import login_required
from .forms import CategoryForm
# Create your views here.

@login_required(login_url='login')
def dashboard(request):
    blogs_count = Blog.objects.all().count()
    category_count = Category.objects.all().count()
    context = {
        'blogs_count': blogs_count,
        'category_count': category_count,
    }
    return render(request, 'dashboard/dashboard.html',context)

def categories(request):
    return render(request, 'dashboard/categories.html')

def posts(request):
    return render(request, 'dashboard/posts.html')

def add_category(request):
    # form = CategoryForm()
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('categories')
    else:
        form = CategoryForm()
    context={
      'form':form
    }
    return render(request, 'dashboard/add_category.html',context)

def edit_category(request,id):
    category=get_object_or_404(Category,id=id)
    form=CategoryForm(instance=category)
    if request.method == 'POST':
        form = CategoryForm(request.POST,instance=category)
        if form.is_valid():
            form.save()
            return redirect('categories')
    context={
        'form':form
    }
    return render(request, 'dashboard/edit_category.html',context)

def delete_category(request,id):
    category=get_object_or_404(Category,id=id)
    category.delete()
    return redirect('categories')
