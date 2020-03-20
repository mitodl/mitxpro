"""
Test end to end django views.
"""
import json
import os

from django.test import Client
from django.urls import reverse
import pytest
from rest_framework import status

from mitxpro.utils import remove_password_from_url

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


def test_webpack_url(mocker, settings, client):
    """Verify that webpack bundle src shows up in production"""
    settings.GA_TRACKING_ID = "fake"
    settings.GTM_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.EMAIL_SUPPORT = "support@text.com"
    settings.USE_WEBPACK_DEV_SERVER = False
    settings.RECAPTCHA_SITE_KEY = "fake_key"
    settings.ZENDESK_CONFIG = {
        "HELP_WIDGET_ENABLED": False,
        "HELP_WIDGET_KEY": "fake_key",
    }
    get_bundle = mocker.patch("mitxpro.templatetags.render_bundle._get_bundle")

    response = client.get(reverse("login"))

    bundles = {bundle[0][1] for bundle in get_bundle.call_args_list}
    assert bundles == {"third_party", "django", "root", "style"}
    js_settings = json.loads(response.context["js_settings_json"])
    assert js_settings == {
        "gaTrackingID": "fake",
        "gtmTrackingID": "fake",
        "public_path": "/static/bundles/",
        "environment": settings.ENVIRONMENT,
        "sentry_dsn": remove_password_from_url(os.environ.get("SENTRY_DSN", "")),
        "release_version": settings.VERSION,
        "recaptchaKey": settings.RECAPTCHA_SITE_KEY,
        "support_email": settings.EMAIL_SUPPORT,
        "site_name": settings.SITE_NAME,
        "zendesk_config": {"help_widget_enabled": False, "help_widget_key": "fake_key"},
    }


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
