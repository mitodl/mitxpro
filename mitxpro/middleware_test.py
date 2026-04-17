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
    ),
    [
        # Matching host → passes through
        (CANONICAL_URL, CANONICAL_HOST, True, False, None),
        # Wrong host + feature enabled → redirect
        (CANONICAL_URL, WRONG_HOST, True, True, f"{CANONICAL_URL}/some/path/"),
        # Wrong host + feature disabled → passes through
        (CANONICAL_URL, WRONG_HOST, False, False, None),
        # No SITE_BASE_URL configured → passes through
        (None, WRONG_HOST, True, False, None),
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
):
    """Tests HostnameRedirectMiddleware redirects or passes through based on host and feature flag."""
    settings.SITE_BASE_URL = site_base_url
    mocker.patch("mitxpro.middleware.is_enabled", return_value=feature_enabled)
    request = rf.get("/some/path/", SERVER_NAME=server_name)
    response = middleware(request)
    if expect_redirect:
        assert response.status_code == status.HTTP_302_FOUND
        assert response["Location"] == expected_location
    else:
        middleware.get_response.assert_called_once_with(request)


def test_redirect_preserves_query_string(rf, settings, middleware, mocker):
    """The redirect preserves the full path including query string."""
    settings.SITE_BASE_URL = CANONICAL_URL
    mocker.patch("mitxpro.middleware.is_enabled", return_value=True)
    request = rf.get(
        "/some/path/", {"foo": "bar", "baz": "qux"}, SERVER_NAME=WRONG_HOST
    )
    response = middleware(request)
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"].startswith(f"{CANONICAL_URL}/some/path/?")
    assert "foo=bar" in response["Location"]
    assert "baz=qux" in response["Location"]
    assert "foo=bar" in response["Location"]
    assert "baz=qux" in response["Location"]
