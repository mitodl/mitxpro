"""Tests for mitxpro middleware"""

import pytest
from rest_framework import status

from mitxpro.middleware import HostnameRedirectMiddleware


CANONICAL_URL = "https://xpro.mit.edu"
CANONICAL_HOST = "xpro.mit.edu"
WRONG_HOST = "xpro-web.odl.mit.edu"


@pytest.fixture()
def middleware(mocker):
    return HostnameRedirectMiddleware(get_response=mocker.Mock(return_value=None))


def test_hostname_matches_no_redirect(rf, settings, middleware, mocker):
    """If the request host matches the canonical host, the request passes through."""
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch(
        "mitxpro.middleware.is_enabled",
        return_value=True,
    )
    request = rf.get("/some/path/", SERVER_NAME=CANONICAL_HOST)
    middleware(request)
    middleware.get_response.assert_called_once_with(request)


def test_wrong_hostname_feature_enabled_redirects(rf, settings, middleware, mocker):
    """If the host is wrong and the feature is enabled, a redirect is returned."""
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch(
        "mitxpro.middleware.is_enabled",
        return_value=True,
    )
    request = rf.get("/some/path/", SERVER_NAME=WRONG_HOST)
    response = middleware(request)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == f"{CANONICAL_URL}/some/path/"


def test_wrong_hostname_feature_disabled_no_redirect(rf, settings, middleware, mocker):
    """If the host is wrong but the feature is disabled, the request passes through."""
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch(
        "mitxpro.middleware.is_enabled",
        return_value=False,
    )
    request = rf.get("/some/path/", SERVER_NAME=WRONG_HOST)
    middleware(request)
    middleware.get_response.assert_called_once_with(request)


def test_no_site_base_url_no_redirect(rf, settings, middleware, mocker):
    """If SITE_BASE_URL is not configured, the request passes through safely."""
    settings.SITE_BASE_URL = None
    mocker.patch(
        "mitxpro.middleware.is_enabled",
        return_value=True,
    )
    request = rf.get("/some/path/", SERVER_NAME=WRONG_HOST)
    middleware(request)
    middleware.get_response.assert_called_once_with(request)


def test_wrong_hostname_preserves_query_string(rf, settings, middleware, mocker):
    """The redirect preserves the full path including query string."""
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch(
        "mitxpro.middleware.is_enabled",
        return_value=True,
    )
    request = rf.get(
        "/some/path/", {"foo": "bar", "baz": "qux"}, SERVER_NAME=WRONG_HOST
    )
    response = middleware(request)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(f"{CANONICAL_URL}/some/path/?")
    assert "foo=bar" in response["Location"]
    assert "baz=qux" in response["Location"]
