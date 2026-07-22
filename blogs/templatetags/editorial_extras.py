from django import template


register = template.Library()


@register.filter(name='category_color')
def category_color(category):
    """Return a stable, distinguishable color for a Category's color-coded tag.

    Requirement 3.3 asks that each post's Category render as a *color-coded*
    tag. The ``Category`` model has no color field, so we derive a deterministic
    hue from the category's primary key (falling back to a hash of its name).
    Using the golden-angle multiplier spreads adjacent ids across the hue
    wheel so neighbouring categories stay visually distinct.

    The returned value is an ``hsl(...)`` string suitable for the
    ``--tag-color`` custom property consumed by ``.category-tag`` in
    ``editorial.css``. Saturation/lightness are fixed at mid values so the
    color stays legible against both the light and dark theme surfaces
    (the flat-fill / hairline-border constraint of the Design System is
    preserved — this only sets a solid hue, not a gradient).
    """
    if category is None:
        return 'var(--color-accent)'

    key = getattr(category, 'pk', None)
    if key is None:
        key = getattr(category, 'id', None)
    if key is None:
        key = abs(hash(str(category)))

    hue = (int(key) * 137) % 360
    return f'hsl({hue}, 52%, 44%)'
