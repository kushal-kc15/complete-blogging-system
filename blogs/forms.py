from django import forms

from .models import Blog, Comment, Contact
from .sanitizers import has_meaningful_rich_text, sanitize_rich_text


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
