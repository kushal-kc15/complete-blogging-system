from django.conf import settings


class SecurityHeadersMiddleware:
    """Attach production-only policy headers configured in Django settings."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()',
        )
        response.setdefault(
            'Content-Security-Policy', settings.CONTENT_SECURITY_POLICY,
        )
        response.setdefault(
            'Cross-Origin-Resource-Policy',
            settings.SECURE_CROSS_ORIGIN_RESOURCE_POLICY,
        )
        return response
