from django import forms
from blogs.models import Blog, Category
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django_ckeditor_5.widgets import CKEditor5Widget
from blogs.forms import RichTextSanitizingFormMixin
from blogs.validators import MAX_IMAGE_SIZE, validate_image_upload


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
            })
        }


class BlogForm(RichTextSanitizingFormMixin, forms.ModelForm):
    MAX_FEATURED_IMAGE_SIZE = MAX_IMAGE_SIZE

    class Meta:
        model = Blog
        fields = ('title', 'category', 'featured_image', 'featured_image_alt',
                  'short_description', 'blog_body', 'status', 'is_featured', 'meta_description')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'featured_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'featured_image_alt': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the image for readers using assistive technology',
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'blog_body': CKEditor5Widget(
                attrs={'class': 'django_ckeditor_5'},
                config_name='extends'
            ),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'blog_body': 'Content',
            'short_description': 'Short Description',
            'is_featured': 'Featured Post',
            'featured_image_alt': 'Featured Image Alt Text',
            'meta_description': 'SEO Description (160 chars)',
        }

    def clean_featured_image(self):
        image = self.cleaned_data.get('featured_image')
        if not image or isinstance(image, str):
            return image
        return validate_image_upload(image)


class AddUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'


class EditUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
