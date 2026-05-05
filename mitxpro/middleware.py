"""Middleware for MIT xPRO"""

from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect


class HostnameRedirectMiddleware:
    """Middleware that redirects requests arriving at an incorrect hostname to the
    canonical hostname configured in SITE_BASE_URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        site_base_url = getattr(settings, "SITE_BASE_URL", None)
        if not site_base_url:
            return self.get_response(request)

        parsed = urlparse(site_base_url)
        canonical_host = parsed.netloc
        canonical_scheme = parsed.scheme

        if request.get_host() == canonical_host:
            return self.get_response(request)

        if not settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED:
            return self.get_response(request)

        redirect_url = "{}://{}{}".format(
            canonical_scheme, canonical_host, request.get_full_path()
        )
        return HttpResponseRedirect(redirect_url)
