from django import template
from django.utils.safestring import mark_safe

from blogs.sanitizers import sanitize_rich_text


register = template.Library()


@register.filter(name='sanitize_rich_text')
def sanitize_rich_text_filter(value):
    """Sanitize legacy rich text immediately before public rendering."""
    return mark_safe(sanitize_rich_text(value))
