from django.shortcuts import render,redirect
from django.contrib import messages
from .forms import RegisterForm
from blogs.models import Category,Blog
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import auth
# from django.http import HttpResponse
def home(request):
    featured_post=Blog.objects.filter(is_featured=True).order_by('updated_at')
    posts=Blog.objects.filter(is_featured=False,status='published').order_by('-updated_at')
    context={
        'featured_post':featured_post,
        'posts':posts,
        }
    return render(request, "home.html",context)

def about(request):
    return render(request, 'about.html')


def Register(request):
    if request.method=='POST':
        form=RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form=RegisterForm()
    context={
        'form':form,
        }
    return render(request, 'register.html',context)

def Login(request):
    if request.method=='POST':
        form=AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password')
            user=auth.authenticate(username=username,password=password)
            if user is not None:
                auth.login(request,user)
                return redirect('home')
            else:
                messages.error(request,'Invalid username or password')
    else:
        form=AuthenticationForm()
    context={
        'form':form,
        }
    return render(request, 'login.html',context)

def Logout(request):
    auth.logout(request)
    return redirect('/')