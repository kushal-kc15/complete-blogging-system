from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm, UserProfileForm, ChangePasswordForm
from blogs.models import Category, Blog, UserProfile
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import auth
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme


# from django.http import HttpResponse
def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        'Allow: /sitemap.xml',
        'Allow: /feed/',
        'Disallow: /admin/',
        'Disallow: /dashboard/',
        'Disallow: /login/',
        'Disallow: /register/',
        'Disallow: /logout/',
        'Disallow: /profile/',
        'Disallow: /password-reset/',
        'Disallow: /password-reset-confirm/',
        'Disallow: /blogs/search/',
        'Disallow: /category/my-bookmarks/',
        'Sitemap: {}://{}/sitemap.xml'.format(request.scheme, request.get_host()),
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def home(request):
    featured_post = Blog.objects.published().filter(
        is_featured=True).order_by('-updated_at')
    posts_list = Blog.objects.published().filter(
        is_featured=False).order_by('-updated_at')

    # Pagination
    paginator = Paginator(posts_list, 6)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    context = {
        'featured_post': featured_post,
        'posts': posts,
    }
    return render(request, "home.html", context)


def about(request):
    return render(request, 'about.html')


def Register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            messages.success(
                request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = RegisterForm()
    context = {
        'form': form,
    }
    return render(request, 'register.html', context)


def Login(request):
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                auth.login(request, user)
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password')
    else:
        form = AuthenticationForm()
    context = {
        'form': form,
        'next': next_url,
    }
    return render(request, 'login.html', context)


@require_POST
def Logout(request):
    auth.logout(request)
    return redirect('/')


# ========== User Profile Views ==========
@login_required
def profile(request):
    """View user profile"""
    user = request.user
    # Ensure profile exists
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)

    context = {
        'user': user,
        'profile': user.profile,
    }
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    user = request.user
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)

    if request.method == 'POST':
        form = UserProfileForm(
            request.POST, request.FILES, instance=user.profile, user=user)
        if form.is_valid():
            # Update user fields
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user.profile, user=user)

    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'edit_profile.html', context)


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Update session to prevent logout
            auth.update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
    else:
        form = ChangePasswordForm(request.user)

    context = {
        'form': form,
    }
    return render(request, 'change_password.html', context)
