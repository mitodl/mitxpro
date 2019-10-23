"""Sheets app util function tests"""

from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
)
from sheets import utils


def test_generate_google_client_config(settings):
    """generate_google_client_config should return a dict with expected values"""
    settings.DRIVE_CLIENT_ID = "some-id"
    settings.DRIVE_CLIENT_SECRET = "some-secret"
    settings.DRIVE_API_PROJECT_ID = "some-project-id"
    settings.SITE_BASE_URL = "http://example.com"
    assert utils.generate_google_client_config() == {
        "web": {
            "client_id": "some-id",
            "client_secret": "some-secret",
            "project_id": "some-project-id",
            "redirect_uris": ["http://example.com/api/sheets/auth-complete/"],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        }
    }
