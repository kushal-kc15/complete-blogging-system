from django import template


register = template.Library()


@register.filter(name='category_color')
def category_color(category):
    if category is None:
        return 'var(--color-accent)'

    key = getattr(category, 'pk', None) or getattr(category, 'id', None)
    if key is None:
        key = abs(hash(str(category)))

    hue = (int(key) * 137) % 360
    return f'hsl({hue}, 45%, 42%)'
