from django.contrib import admin
from . models import Category,Blog
# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
  list_display = ['name','created_at','updated_at']
  
admin.site.register(Category,CategoryAdmin)

class BlogAdmin(admin.ModelAdmin):
  list_display = ['title','category','author','created_at','updated_at']
admin.site.register(Blog,BlogAdmin)