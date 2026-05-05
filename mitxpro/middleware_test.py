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


@pytest.mark.parametrize(
    (
        "site_base_url",
        "server_name",
        "redirect_enabled",
        "expect_redirect",
        "expected_location",
    ),
    [
        # Matching host -> passes through
        (CANONICAL_URL, CANONICAL_HOST, True, False, None),
        # Wrong host + redirect enabled -> redirect
        (CANONICAL_URL, WRONG_HOST, True, True, f"{CANONICAL_URL}/some/path/"),
        # Wrong host + redirect disabled -> passes through
        (CANONICAL_URL, WRONG_HOST, False, False, None),
        # No SITE_BASE_URL configured -> passes through
        (None, WRONG_HOST, True, False, None),
    ],
)
def test_hostname_redirect_middleware(
    rf,
    settings,
    middleware,
    site_base_url,
    server_name,
    redirect_enabled,
    expect_redirect,
    expected_location,
):
    """Tests HostnameRedirectMiddleware redirects or passes through based on host and setting."""
    settings.SITE_BASE_URL = site_base_url
    settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED = redirect_enabled
    request = rf.get("/some/path/", SERVER_NAME=server_name)
    response = middleware(request)

    if expect_redirect:
        assert response.status_code == status.HTTP_302_FOUND
        assert response["Location"] == expected_location
    else:
        middleware.get_response.assert_called_once_with(request)


def test_redirect_preserves_query_string(rf, settings, middleware):
    """The redirect preserves the full path including query string."""
    settings.SITE_BASE_URL = CANONICAL_URL
    settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED = True
    request = rf.get(
        "/some/path/", {"foo": "bar", "baz": "qux"}, SERVER_NAME=WRONG_HOST
    )
    response = middleware(request)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(f"{CANONICAL_URL}/some/path/?")
    assert "foo=bar" in response["Location"]
    assert "baz=qux" in response["Location"]


def test_api_path_bypasses_redirect_checks(rf, settings, middleware):
    """API routes still follow the same redirect setting behavior."""
    settings.SITE_BASE_URL = CANONICAL_URL
    settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED = True
    request = rf.get("/api/v1/topics/", SERVER_NAME=WRONG_HOST)
    response = middleware(request)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == f"{CANONICAL_URL}/api/v1/topics/"


def test_hostname_redirect_checks_actual_http_host(rf, settings, middleware):
    """Redirect decision is based on actual HTTP_HOST, not X-Forwarded-Host.

    This prevents infinite redirects when X-Forwarded-Host persists through
    redirects in proxy scenarios. The middleware checks the real incoming
    HTTP_HOST header, not Django's interpretation via request.get_host()
    which respects USE_X_FORWARDED_HOST.
    """
    settings.SITE_BASE_URL = CANONICAL_URL
    settings.CANONICAL_HOSTNAME_REDIRECT_ENABLED = True
    # Create request with wrong actual HTTP_HOST
    request = rf.get("/some/path/")
    # Manually set the actual HTTP_HOST to a non-canonical value
    request.META["HTTP_HOST"] = WRONG_HOST
    response = middleware(request)
    # Should redirect because actual HTTP_HOST doesn't match canonical
    assert response.status_code == 302
    assert response["Location"] == f"{CANONICAL_URL}/some/path/"
