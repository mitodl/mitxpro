"""Utility functions for the courseware app"""
from urllib.parse import urljoin

from django.conf import settings


def edx_url(path):
    """Returns the full url to the provided path"""  # noqa: D401
    return urljoin(settings.OPENEDX_API_BASE_URL, path)


def edx_redirect_url(path):
    """Returns the full url to the provided path using the edX hostname specified for redirects"""  # noqa: D401
    return urljoin(settings.OPENEDX_BASE_REDIRECT_URL, path)
