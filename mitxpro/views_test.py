"""
Test end to end django views.
"""

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.django_db]


def test_index_view(client):
    """Verify the index view is as expected"""
    response = client.get(reverse("wagtail_serve", args=[""]))
    assert response.status_code == 200


def test_not_found_view(client):
    """
    Test that the 404 view fetches correct template.
    """
    resp = client.get("/some/not/found/url/")
    assert resp.templates[0].name == "404.html"
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    ("add_coupon", "change_coupon", "expected_admin_status", "expected_coupons_status", "expected_deactivate_status"),
    [
        (True, False, 200, 200, 403),
        (False, True, 200, 403, 200),
        (False, False, 403, 403, 403),
        (True, True, 200, 200, 200),
    ]
)
def test_ecommerce_restricted_view(user, add_coupon, change_coupon, expected_admin_status, expected_coupons_status, expected_deactivate_status):   #noqa: PLR0913
    """Test that the ecommerce restricted view is only accessible with the right permissions."""

    user.user_permissions.clear()

    if add_coupon:
        user.user_permissions.add(Permission.objects.get(codename="add_coupon"))
    if change_coupon:
        user.user_permissions.add(Permission.objects.get(codename="change_coupon"))

    client = Client()
    client.force_login(user)

    ecommerce_admin_url = reverse("ecommerce-admin")
    add_coupons_url = ecommerce_admin_url + "coupons"
    deactivate_coupons_url = ecommerce_admin_url + "deactivate-coupons"

    assert client.get(ecommerce_admin_url).status_code == expected_admin_status
    assert client.get(add_coupons_url).status_code == expected_coupons_status
    assert client.get(deactivate_coupons_url).status_code == expected_deactivate_status


def test_cms_signin_redirect_to_site_signin(client):
    """
    Test that the cms/login redirects users to site signin page.
    """
    response = client.get("/cms", follow=True)
    assert response.request["PATH_INFO"] == "/signin/"


def test_app_context(settings, client):
    """Tests the app context API"""
    settings.GA_TRACKING_ID = "fake"
    settings.GTM_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.WEBPACK_USE_DEV_SERVER = False

    response = client.get(reverse("api-app_context"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "features": {},
        "ga_tracking_id": "fake",
        "gtm_tracking_id": "fake",
        "public_path": "/static/bundles/",
        "environment": settings.ENVIRONMENT,
        "release_version": settings.VERSION,
    }


@pytest.mark.parametrize("verb", ["get", "post"])
def test_dashboard(verb):
    """Anonymous users should be able to POST to the dashboard and see the same content as a GET"""
    client = Client(enforce_csrf_checks=True)
    method = getattr(client, verb)
    response = method(reverse("user-dashboard"))
    assert response.status_code == status.HTTP_200_OK
