from django.contrib import admin
from . models import Category,Blog
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

