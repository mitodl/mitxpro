"""
Test end to end django views.
"""
import json

from django.test import Client
from django.urls import reverse
import pytest
from rest_framework import status


pytestmark = [pytest.mark.django_db]


def test_index_view(client):
    """Verify the index view is as expected"""
    response = client.get(reverse("mitxpro-index"))
    assert response.status_code == 200


def test_restricted_view(client, admin_client):
    """Verify the restricted view is only available to admins"""
    assert client.get(reverse("ecommerce-admin")).status_code == 403
    assert admin_client.get(reverse("ecommerce-admin")).status_code == 200


def test_webpack_url(mocker, settings, client):
    """Verify that webpack bundle src shows up in production"""
    settings.GA_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.USE_WEBPACK_DEV_SERVER = False
    settings.RECAPTCHA_SITE_KEY = "fake_key"
    get_bundle = mocker.patch("mitxpro.templatetags.render_bundle._get_bundle")

    response = client.get(reverse("login"))

    bundles = {bundle[0][1] for bundle in get_bundle.call_args_list}
    assert bundles == {"root", "style"}
    js_settings = json.loads(response.context["js_settings_json"])
    assert js_settings == {
        "gaTrackingID": "fake",
        "public_path": "/static/bundles/",
        "environment": settings.ENVIRONMENT,
        "sentry_dsn": None,
        "release_version": settings.VERSION,
        "recaptchaKey": settings.RECAPTCHA_SITE_KEY,
    }


def test_app_context(settings, client):
    """Tests the app context API"""
    settings.GA_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.USE_WEBPACK_DEV_SERVER = False

    response = client.get(reverse("api-app_context"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "features": {},
        "ga_tracking_id": "fake",
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
