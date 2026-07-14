"""Shared allowlist policy for user-authored rich article content."""

from html.parser import HTMLParser
from urllib.parse import urlsplit

import nh3


# This mirrors the safe subset of the CKEditor toolbar. Expanding it requires
# a security review and regression tests because rendered content is public.
ALLOWED_TAGS = {
    'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'blockquote', 'ul', 'ol', 'li', 'hr', 'pre', 'code',
    'a', 'figure', 'figcaption', 'img',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'},
    'img': {'src', 'alt', 'title', 'width', 'height'},
    'figure': {'class'},
    'th': {'colspan', 'rowspan'},
    'td': {'colspan', 'rowspan'},
}

CLEAN_CONTENT_TAGS = {
    'script', 'style', 'iframe', 'object', 'embed', 'form', 'input',
    'button', 'textarea', 'select', 'option', 'link', 'meta', 'base',
    'svg', 'math', 'video', 'audio', 'source',
}


def _safe_url(tag, value):
    parsed = urlsplit(value)
    if value.startswith('//'):
        return None
    if not parsed.scheme:
        return value
    scheme = parsed.scheme.lower()
    if tag == 'a' and scheme in {'http', 'https', 'mailto'}:
        return value
    if tag == 'img' and scheme in {'http', 'https'}:
        return value
    return None


def _attribute_filter(tag, attribute, value):
    if attribute == 'class':
        allowed_classes = {
            'image', 'image-style-align-left', 'image-style-align-right',
            'image-style-align-center', 'image-style-side', 'table',
        }
        classes = value.split()
        if tag == 'figure' and classes and set(classes).issubset(allowed_classes):
            return ' '.join(classes)
        return None
    if attribute in {'href', 'src'}:
        return _safe_url(tag, value)
    if attribute in {'width', 'height'}:
        return value if value.isdigit() else None
    return value


def sanitize_rich_text(html):
    """Return public-safe HTML without marking it safe for template output."""
    return nh3.clean(
        html or '',
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        clean_content_tags=CLEAN_CONTENT_TAGS,
        attribute_filter=_attribute_filter,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer',
    )


class _MeaningfulContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_content = False

    def handle_data(self, data):
        if data.strip():
            self.has_content = True

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and dict(attrs).get('alt', '').strip():
            self.has_content = True


def has_meaningful_rich_text(html):
    """Treat text or an image with useful alt text as meaningful article content."""
    parser = _MeaningfulContentParser()
    parser.feed(html or '')
    return parser.has_content
