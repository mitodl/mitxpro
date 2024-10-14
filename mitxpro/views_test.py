"""
Test end to end django views.
"""

import pytest
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
