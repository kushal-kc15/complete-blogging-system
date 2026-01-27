from django.contrib import admin
from . models import Category,Blog,Comment
# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
  list_display = ['id','name','created_at','updated_at']
  
admin.site.register(Category,CategoryAdmin)

class BlogAdmin(admin.ModelAdmin):
  list_display = ['title','category','author','created_at','updated_at','is_featured','status']
  prepopulated_fields = {'slug':('title',)}
  search_fields = ['id','title','category__name','status','is_featured']
  list_filter = ['title','category','created_at','updated_at','is_featured','status']
  list_editable = ['is_featured','status']
admin.site.register(Blog,BlogAdmin)

class CommentAdmin(admin.ModelAdmin):
  list_display = ['user','blog','created_at','updated_at']
  search_fields = ['user__username','blog__title','Comment']
  list_filter = ['created_at','updated_at']
admin.site.register(Comment,CommentAdmin)