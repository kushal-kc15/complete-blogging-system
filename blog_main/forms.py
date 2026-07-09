from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from blogs.models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    MAX_AVATAR_SIZE = 3 * 1024 * 1024
    ALLOWED_AVATAR_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    ALLOWED_AVATAR_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'you@example.com'}
        ),
    )

    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'website', 'location']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about yourself...'}),
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://yourwebsite.com'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, Country'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and not self.is_bound:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email:
            users = User.objects.filter(email__iexact=email)
            if self.user:
                users = users.exclude(pk=self.user.pk)
            if users.exists():
                raise forms.ValidationError('This email is already registered.')
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar or isinstance(avatar, str):
            return avatar

        content_type = getattr(avatar, 'content_type', '')
        image_format = getattr(getattr(avatar, 'image', None), 'format', '')
        if (
            content_type not in self.ALLOWED_AVATAR_TYPES or
            image_format not in self.ALLOWED_AVATAR_FORMATS
        ):
            raise forms.ValidationError('Upload a JPEG, PNG, or WebP avatar image.')

        if avatar.size > self.MAX_AVATAR_SIZE:
            raise forms.ValidationError('Avatar image must be 3 MB or smaller.')

        return avatar


class ChangePasswordForm(PasswordChangeForm):
    """Custom password change form"""
    old_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Current Password'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'New Password'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )
