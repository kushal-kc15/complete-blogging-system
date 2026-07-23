"""
URL configuration for blog_main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, reverse_lazy, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from blogs import views as BlogsView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import BlogSitemap, StaticViewSitemap
from .feeds import LatestPostsFeed

sitemaps = {
    'blogs': BlogSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('', views.home, name='home'),
    path('category/', include('blogs.urls')),

    # Legacy URLs kept for old bookmarks/links; django-allauth now owns
    # authentication. Custom Register/Login/Logout views have been removed.
    path('login/', RedirectView.as_view(
        url=reverse_lazy('account_login'), query_string=True), name='login'),
    path('register/', RedirectView.as_view(
        url=reverse_lazy('account_signup'), query_string=True), name='register'),
    path('logout/', RedirectView.as_view(
        url=reverse_lazy('account_logout'), query_string=True), name='logout'),

    path('accounts/', include('allauth.urls')),
    path('password-reset/', views.RateLimitedPasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    path('dashboard/', include('dashboard.urls')),
    path('about/', views.about, name='about'),
    path('contact/', BlogsView.contact, name='contact'),

    # User Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/set-password/', views.set_password, name='set_password'),

    path('ckeditor5/image_upload/', views.ckeditor_image_upload,
         name='ck_editor_5_upload_file'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('feed/', LatestPostsFeed(), name='rss_feed'),
    path('authors/<str:username>/', BlogsView.AuthorProfile, name='author_profile'),
    path('authors/<str:username>/follow/', BlogsView.follow_author, name='follow_author'),
    path('authors/<str:username>/unfollow/', BlogsView.unfollow_author, name='unfollow_author'),
    path('following/', BlogsView.following_feed, name='following_feed'),
    path('categories/', BlogsView.category_index, name='category_index'),
    path('<slug:slug>/', BlogsView.BlogDetail, name='Blog_detail'),
    path('blogs/search/', BlogsView.Search, name='search'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
