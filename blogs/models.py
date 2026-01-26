from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Category(models.Model):
  name = models.CharField(max_length=100,unique=True)
  created_at=models.DateTimeField(auto_now_add=True)
  updated_at=models.DateTimeField(auto_now=True)

  class Meta:
    verbose_name = "Category"
    verbose_name_plural = "Categories"
  
  def __str__(self):
    return self.name


STATUS_CHOICES=(
  ('draft','Draft'),
  ('published','Published'),
)
class Blog(models.Model):
  title=models.CharField(max_length=200)
  slug=models.SlugField(max_length=200,unique=True)
  category=models.ForeignKey(Category,on_delete=models.CASCADE)
  author=models.ForeignKey(User,on_delete=models.CASCADE)
  created_at=models.DateTimeField(auto_now_add=True)
  updated_at=models.DateTimeField(auto_now=True)
  featured_image=models.ImageField(upload_to='uploads/%Y/%m/%d',blank=True,null=True)
  blog_body=models.TextField(max_length=2000)
  short_description=models.TextField(max_length=500)
  status=models.CharField(max_length=10,choices=STATUS_CHOICES,default='draft')
  is_featured=models.BooleanField(default=False)

  class Meta:
    verbose_name = "Blog"
    verbose_name_plural = "Blogs"
  
  def __str__(self):
    return self.title

