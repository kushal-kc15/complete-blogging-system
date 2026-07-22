"""Signal receivers for the blogs app.

The only receiver here handles new sign-ups that come through django-allauth
(most importantly Google social sign-ups). It guarantees the new user has a
``UserProfile`` and copies the Google-provided name into the account.

The project's own username/password ``Register`` view already creates the
profile explicitly, and the profile/edit views create one lazily as a safety
net, so this receiver intentionally does NOT hook the global ``User`` post_save
signal (doing so would collide with those explicit ``UserProfile.objects.create``
calls and raise IntegrityError).
"""
from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from .models import UserProfile


@receiver(user_signed_up)
def ensure_profile_on_signup(request, user, sociallogin=None, **kwargs):
    """Create the UserProfile for an allauth sign-up and import Google data."""
    UserProfile.objects.get_or_create(user=user)

    if sociallogin is None:
        return

    # Google returns the account holder's name split into given/family parts.
    extra = getattr(sociallogin.account, 'extra_data', {}) or {}
    fields_to_update = []
    if not user.first_name and extra.get('given_name'):
        user.first_name = extra['given_name'][:30]
        fields_to_update.append('first_name')
    if not user.last_name and extra.get('family_name'):
        user.last_name = extra['family_name'][:30]
        fields_to_update.append('last_name')
    if fields_to_update:
        user.save(update_fields=fields_to_update)
