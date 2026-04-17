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
        "feature_enabled",
        "expect_redirect",
        "expected_location",
        "expect_is_enabled_called",
    ),
    [
        # Matching host → passes through
        (CANONICAL_URL, CANONICAL_HOST, True, False, None, False),
        # Wrong host + feature enabled → redirect
        (CANONICAL_URL, WRONG_HOST, True, True, f"{CANONICAL_URL}/some/path/", True),
        # Wrong host + feature disabled → passes through
        (CANONICAL_URL, WRONG_HOST, False, False, None, True),
        # No SITE_BASE_URL configured → passes through
        (None, WRONG_HOST, True, False, None, False),
    ],
)
def test_hostname_redirect_middleware(
    rf,
    settings,
    middleware,
    mocker,
    site_base_url,
    server_name,
    feature_enabled,
    expect_redirect,
    expected_location,
    expect_is_enabled_called,
):
    """Tests HostnameRedirectMiddleware redirects or passes through based on host and feature flag."""
    settings.SITE_BASE_URL = site_base_url
    is_enabled_mock = mocker.patch(
        "mitxpro.middleware.is_enabled", return_value=feature_enabled
    )
    request = rf.get("/some/path/", SERVER_NAME=server_name)
    response = middleware(request)

    if expect_is_enabled_called:
        is_enabled_mock.assert_called_once_with("xpro-hostname-redirect", default=True)
    else:
        is_enabled_mock.assert_not_called()

    if expect_redirect:
        assert response.status_code == status.HTTP_302_FOUND
        assert response["Location"] == expected_location
    else:
        middleware.get_response.assert_called_once_with(request)


def test_redirect_preserves_query_string(rf, settings, middleware, mocker):
    """The redirect preserves the full path including query string."""
    settings.SITE_BASE_URL = CANONICAL_URL
    is_enabled_mock = mocker.patch("mitxpro.middleware.is_enabled", return_value=True)
    request = rf.get(
        "/some/path/", {"foo": "bar", "baz": "qux"}, SERVER_NAME=WRONG_HOST
    )
    response = middleware(request)
    is_enabled_mock.assert_called_once_with("xpro-hostname-redirect", default=True)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(f"{CANONICAL_URL}/some/path/?")
    assert "foo=bar" in response["Location"]
    assert "baz=qux" in response["Location"]


def test_api_path_bypasses_redirect_checks(rf, settings, middleware, mocker):
    """API routes bypass redirect and feature-flag checks for performance."""
    settings.SITE_BASE_URL = CANONICAL_URL
    is_enabled_mock = mocker.patch("mitxpro.middleware.is_enabled", return_value=True)
    request = rf.get("/api/v1/topics/", SERVER_NAME=WRONG_HOST)
    middleware(request)
    is_enabled_mock.assert_not_called()
    middleware.get_response.assert_called_once_with(request)


def test_hostname_redirect_checks_actual_http_host(rf, settings, middleware, mocker):
    """Redirect decision is based on actual HTTP_HOST, not X-Forwarded-Host.

    This prevents infinite redirects when X-Forwarded-Host persists through
    redirects in proxy scenarios. The middleware checks the real incoming
    HTTP_HOST header, not Django's interpretation via request.get_host()
    which respects USE_X_FORWARDED_HOST.
    """
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch("mitxpro.middleware.is_enabled", return_value=True)
    # Create request with wrong actual HTTP_HOST
    request = rf.get("/some/path/")
    # Manually set the actual HTTP_HOST to a non-canonical value
    request.META["HTTP_HOST"] = WRONG_HOST
    response = middleware(request)
    # Should redirect because actual HTTP_HOST doesn't match canonical
    assert response.status_code == 302
    assert response["Location"] == f"{CANONICAL_URL}/some/path/"
