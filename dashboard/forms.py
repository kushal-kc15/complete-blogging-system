from django import forms
from django.utils import timezone
from blogs.models import Blog, Category, Series
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django_ckeditor_5.widgets import CKEditor5Widget
from blogs.forms import RichTextSanitizingFormMixin
from blogs.validators import MAX_IMAGE_SIZE, validate_image_upload

# datetime-local inputs exchange values in this format (no seconds/timezone).
DATETIME_LOCAL_FORMAT = '%Y-%m-%dT%H:%M'


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

    # Publication_Time control bound to the model's ``published_at`` field.
    # Presented as a datetime-local widget so editors can schedule a post to
    # go live at a future date/time (Requirements 12.1, 12.2).
    publication_time = forms.DateTimeField(
        required=False,
        label='Publication Time',
        help_text=(
            'Schedule this post to go live at a future date and time. '
            'Leave blank to publish immediately (when status is Published) '
            'or to keep the post as a draft.'
        ),
        input_formats=[DATETIME_LOCAL_FORMAT, '%Y-%m-%dT%H:%M:%S'],
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=DATETIME_LOCAL_FORMAT,
        ),
    )

    class Meta:
        model = Blog
        fields = ('title', 'category', 'series', 'series_order', 'featured_image', 'featured_image_alt',
                  'short_description', 'blog_body', 'status', 'is_featured', 'meta_description')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'series': forms.Select(attrs={
                'class': 'form-control'
            }),
            'series_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Part number in series',
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
            'series': 'Series (optional)',
            'series_order': 'Part number',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['series'].queryset = Series.objects.filter(author=self.user)
        # Pre-fill the control when editing a Scheduled_Blog (status published
        # with a future published_at) so the editor can view/change/clear the
        # scheduled Publication_Time (Requirement 12.2).
        instance = getattr(self, 'instance', None)
        if instance is not None and instance.pk and instance.published_at:
            if instance.published_at > timezone.now():
                self.initial.setdefault('publication_time', instance.published_at)

    def clean_featured_image(self):
        image = self.cleaned_data.get('featured_image')
        if not image or isinstance(image, str):
            return image
        return validate_image_upload(image)

    def clean_publication_time(self):
        value = self.cleaned_data.get('publication_time')
        # Normalize to a timezone-aware datetime so comparisons against
        # timezone.now() are unambiguous around the scheduling boundary.
        if value is not None and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return value

    def _is_already_published(self):
        """A post is already published when it is live (status published with a
        Publication_Time at or before now). Editing such a post must not be
        rejected for having a past Publication_Time (Requirement 12.3)."""
        instance = getattr(self, 'instance', None)
        return bool(
            instance is not None
            and instance.pk
            and instance.status == 'published'
            and instance.published_at is not None
            and instance.published_at <= timezone.now()
        )

    def clean(self):
        cleaned_data = super().clean()
        publication_time = cleaned_data.get('publication_time')

        # Reject a past Publication_Time for a post that is not already
        # published (Requirement 12.3).
        if publication_time is not None and not self._is_already_published():
            if publication_time <= timezone.now():
                self.add_error(
                    'publication_time',
                    'Publication Time must be in the future.',
                )
        return cleaned_data

    def save(self, commit=True):
        blog = super().save(commit=False)
        publication_time = self.cleaned_data.get('publication_time')
        status = self.cleaned_data.get('status')

        if publication_time is not None:
            # A Publication_Time was supplied: schedule (or, for an already
            # published post, retime) the post. status=published + future
            # published_at yields a Scheduled_Blog (Requirements 12.1, 12.2).
            blog.status = 'published'
            blog.published_at = publication_time
        elif status == 'published':
            # Publish now. Clear any previously scheduled future time so
            # Blog.save() records published_at as the current time.
            blog.status = 'published'
            if blog.published_at is not None and blog.published_at > timezone.now():
                blog.published_at = None
        else:
            # Publication_Time cleared without publishing: normalize to a
            # draft rather than leaving an ambiguous scheduled state
            # (Requirement 12.4).
            blog.status = 'draft'
            blog.published_at = None

        if commit:
            blog.save()
            self.save_m2m()
        return blog


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
