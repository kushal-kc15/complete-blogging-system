from django.contrib import admin
from .models import Category, Blog, Comment, Like, Bookmark, Contact, UserProfile
from .forms import BlogAdminForm


# Register your models here.

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'created_at']
    search_fields = ['user__username', 'user__email', 'location']
    list_filter = ['created_at']


admin.site.register(UserProfile, UserProfileAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at', 'updated_at']


admin.site.register(Category, CategoryAdmin)


class BlogAdmin(admin.ModelAdmin):
    form = BlogAdminForm
    list_display = ['title', 'category', 'author', 'views',
                    'created_at', 'updated_at', 'is_featured', 'status']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['id', 'title', 'category__name', 'status', 'is_featured']
    list_filter = ['title', 'category', 'created_at',
                   'updated_at', 'is_featured', 'status']
    list_editable = ['is_featured', 'status']


admin.site.register(Blog, BlogAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'blog', 'parent', 'is_visible', 'created_at', 'updated_at']
    search_fields = ['user__username', 'blog__title', 'comment']
    list_filter = ['is_visible', 'created_at', 'updated_at']
    list_editable = ['is_visible']


admin.site.register(Comment, CommentAdmin)


class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'blog', 'created_at']
    search_fields = ['user__username', 'blog__title']


admin.site.register(Like, LikeAdmin)


class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'blog', 'created_at']
    search_fields = ['user__username', 'blog__title']


admin.site.register(Bookmark, BookmarkAdmin)


class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    search_fields = ['name', 'email', 'subject', 'message']
    list_filter = ['is_read', 'created_at']
    list_editable = ['is_read']


admin.site.register(Contact, ContactAdmin)
