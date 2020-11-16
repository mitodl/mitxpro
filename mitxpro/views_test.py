"""
Test end to end django views.
"""
from django.test import Client
from django.urls import reverse
import pytest
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


def test_restricted_view(client, admin_client):
    """Verify the restricted view is only available to admins"""
    assert client.get(reverse("ecommerce-admin")).status_code == 403
    assert admin_client.get(reverse("ecommerce-admin")).status_code == 200


def test_cms_signin_redirect_to_site_signin(client):
    """
    Test that the cms/login redirects users to site signin page.
    """
    response = client.get("/cms", follow=True)
    assert response.request["PATH_INFO"] == "/signin/"


def test_webpack_url(mocker, client):
    """Verify that webpack bundle src shows up in production"""
    get_bundle = mocker.patch("mitxpro.templatetags.render_bundle._get_bundle")

    client.get(reverse("login"))

    bundles = {bundle[0][1] for bundle in get_bundle.call_args_list}
    assert bundles == {"django", "root", "style"}


def test_app_context(settings, client):
    """Tests the app context API"""
    settings.GA_TRACKING_ID = "fake"
    settings.GTM_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.USE_WEBPACK_DEV_SERVER = False

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
