"""Middleware for MIT xPRO"""

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect

log = logging.getLogger(__name__)


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
        request_host = request.get_host()
        if (
            not settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED
            or request_host == canonical_host
        ):
            return self.get_response(request)

        log.info(
            "Hostname redirect: scheme=%s host=%s path=%s -> scheme=%s host=%s path=%s "
            "(forwarded_host=%s forwarded_proto=%s)",
            request.scheme,
            request_host,
            request.path,
            canonical_scheme,
            canonical_host,
            request.path,
            request.META.get("HTTP_X_FORWARDED_HOST"),
            request.META.get("HTTP_X_FORWARDED_PROTO"),
        )
        redirect_url = (
            f"{canonical_scheme}://{canonical_host}{request.get_full_path()}"
        )
        return HttpResponseRedirect(redirect_url)
