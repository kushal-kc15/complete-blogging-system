from math import ceil

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm, UserProfileForm, ChangePasswordForm, SetPasswordForm
from blogs.models import Category, Blog, UserProfile
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.contrib import auth
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.core import get_usage
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django_ckeditor_5.permissions import check_upload_permission
from django.core.files.storage import storages
from blogs.validators import validate_image_upload


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


@require_POST
@check_upload_permission
def ckeditor_image_upload(request):
    upload = request.FILES.get('upload')
    if not upload:
        return JsonResponse({'error': {'message': 'No image was uploaded.'}}, status=400)
    try:
        validate_image_upload(upload)
    except ValidationError as exc:
        return JsonResponse({'error': {'message': exc.messages[0]}}, status=400)

    storage = get_storage_class()()
    filename = storage.save(upload.name, upload)
    return JsonResponse({'url': storage.url(filename)})


HOME_FEATURED_POST_LIMIT = 7
HOME_TOP_CATEGORIES_LIMIT = 8


def home(request):
    # home.html renders post.author and post.category for every featured
    # and latest post, so select_related avoids a query per post for each
    # of those foreign keys. The featured-post section previously rendered
    # every featured post with no limit; it's capped here to a reasonable
    # number (1 hero post + up to 6 cards) so a large number of featured
    # posts can't turn the homepage into an unbounded listing page.
    featured_post = Blog.objects.published().filter(
        is_featured=True
    ).select_related('author', 'category').order_by('-updated_at')[:HOME_FEATURED_POST_LIMIT]
    posts_list = Blog.objects.published().filter(
        is_featured=False
    ).select_related('author', 'category').annotate(
        total_likes=Count('likes', distinct=True)
    ).order_by('-updated_at')

    # Pagination
    paginator = Paginator(posts_list, 6)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    # Top categories for the homepage: annotate each category with a count
    # of its published posts only (drafts never count via the filtered
    # Count), drop categories with zero published posts, order by that
    # count descending with category name as the alphabetical tie-break,
    # and cap the result to a small, homepage-appropriate number.
    top_categories = Category.objects.annotate(
        published_post_count=Count(
            'blog', filter=Q(blog__status='published')
        )
    ).filter(published_post_count__gt=0).order_by(
        '-published_post_count', 'name'
    )[:HOME_TOP_CATEGORIES_LIMIT]

    context = {
        'featured_post': featured_post,
        'posts': posts,
        'top_categories': top_categories,
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


def _normalized_login_identifier(request):
    value = request.POST.get('username', '')
    try:
        value = str(value)
    except (TypeError, ValueError):
        value = ''
    return value.strip().casefold() or '<missing>'


def _login_identity_key(group, request):
    client_ip = request.META.get('REMOTE_ADDR', '')
    return f'{client_ip}:{_normalized_login_identifier(request)}'


def _login_rate_usage(request, *, group, key, rate, increment):
    return get_usage(
        request,
        group=group,
        key=key,
        rate=rate,
        method=('POST',),
        increment=increment,
    )


def _login_rate_limited_response(request, form, next_url, usages):
    form.add_error(
        None, 'Too many unsuccessful login attempts. Please wait and try again.'
    )
    response = render(
        request,
        'login.html',
        {'form': form, 'next': next_url, 'login_rate_limited': True},
        status=429,
    )
    time_left = max(
        (usage.get('time_left', 0) for usage in usages if usage), default=0
    )
    if time_left > 0:
        response['Retry-After'] = str(max(1, ceil(time_left)))
    return response


class RateLimitedPasswordResetView(PasswordResetView):
    def post(self, request, *args, **kwargs):
        usage = get_usage(
            request,
            group='password-reset-request',
            key='ip',
            rate=settings.PASSWORD_RESET_RATE,
            method=('POST',),
            increment=True,
        )
        if usage and usage['should_limit']:
            form = self.get_form()
            form.add_error(
                None, 'Too many password reset requests. Please wait and try again.'
            )
            response = self.render_to_response(
                self.get_context_data(form=form), status=429
            )
            time_left = usage.get('time_left', 0)
            if time_left > 0:
                response['Retry-After'] = str(max(1, ceil(time_left)))
            return response
        return super().post(request, *args, **kwargs)


def Login(request):
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        identifier = _normalized_login_identifier(request)
        has_identifier = identifier != '<missing>'
        has_password = bool(request.POST.get('password'))
        usages = []

        if has_identifier:
            usages.append(_login_rate_usage(
                request,
                group='login-failure-ip',
                key='ip',
                rate=settings.LOGIN_FAILURE_IP_RATE,
                increment=False,
            ))
        if has_identifier and has_password:
            usages.append(_login_rate_usage(
                request,
                group='login-failure-identity',
                key=_login_identity_key,
                rate=settings.LOGIN_FAILURE_IDENTITY_RATE,
                increment=False,
            ))
        if any(usage and usage['should_limit'] for usage in usages):
            return _login_rate_limited_response(request, form, next_url, usages)

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
        elif has_identifier:
            usages = [
                _login_rate_usage(
                    request,
                    group='login-failure-ip',
                    key='ip',
                    rate=settings.LOGIN_FAILURE_IP_RATE,
                    increment=True,
                )
            ]
            if has_password:
                usages.append(_login_rate_usage(
                    request,
                    group='login-failure-identity',
                    key=_login_identity_key,
                    rate=settings.LOGIN_FAILURE_IDENTITY_RATE,
                    increment=True,
                ))
            if any(usage and usage['should_limit'] for usage in usages):
                return _login_rate_limited_response(request, form, next_url, usages)
    else:
        form = AuthenticationForm()
    context = {
        'form': form,
        'next': next_url,
        'login_rate_limited': False,
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

    google_account = SocialAccount.objects.filter(
        user=user, provider='google'
    ).first()

    context = {
        'user': user,
        'profile': user.profile,
        'google_account': google_account,
        'has_usable_password': user.has_usable_password(),
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
    # Social-only accounts have no usable password to change; send them to the
    # set-password flow instead (which does not ask for a current password).
    if not request.user.has_usable_password():
        return redirect('set_password')

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


@login_required
def set_password(request):
    """Set an initial password for a social-only account.

    Users who registered through Google have no usable password. This lets
    them create one so they can also log in with username + password.
    """
    # Users who already have a password should use the change-password flow.
    if request.user.has_usable_password():
        return redirect('change_password')

    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            auth.update_session_auth_hash(request, request.user)
            messages.success(
                request,
                'Password set successfully! You can now also log in with your '
                'username and password.',
            )
            return redirect('profile')
    else:
        form = SetPasswordForm(request.user)

    context = {
        'form': form,
    }
    return render(request, 'set_password.html', context)
