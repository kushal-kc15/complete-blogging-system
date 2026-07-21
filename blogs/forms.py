from django import forms

from .models import Blog, Comment, Contact
from .sanitizers import has_meaningful_rich_text, sanitize_rich_text
from .validators import validate_image_upload


class RichTextSanitizingFormMixin:
    def clean_blog_body(self):
        sanitized = sanitize_rich_text(self.cleaned_data.get('blog_body'))
        if not has_meaningful_rich_text(sanitized):
            raise forms.ValidationError(
                'Content must include text or an image with meaningful alt text.'
            )
        return sanitized


class BlogAdminForm(RichTextSanitizingFormMixin, forms.ModelForm):
    class Meta:
        model = Blog
        fields = '__all__'

    def clean_featured_image(self):
        image = self.cleaned_data.get('featured_image')
        if not image or isinstance(image, str):
            return image
        return validate_image_upload(image)


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ('name', 'email', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('comment',)
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your comment',
            }),
        }
