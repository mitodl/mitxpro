"""Middleware for MIT xPRO"""

from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect

from mitol.olposthog.features import is_enabled

from mitxpro import features


class HostnameRedirectMiddleware:
    """Middleware that redirects requests arriving at an incorrect hostname to the
    canonical hostname configured in SITE_BASE_URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_enabled(features.HOSTNAME_REDIRECT, default=False):
            return self.get_response(request)

        site_base_url = getattr(settings, "SITE_BASE_URL", None)
        if not site_base_url:
            return self.get_response(request)

        parsed = urlparse(site_base_url)
        canonical_host = parsed.netloc
        canonical_scheme = parsed.scheme

        if request.get_host() != canonical_host:
            redirect_url = "{}://{}{}".format(
                canonical_scheme, canonical_host, request.get_full_path()
            )
            return HttpResponseRedirect(redirect_url)

        return self.get_response(request)
