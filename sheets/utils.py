"""Sheets app util functions"""
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse

from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
)


def generate_google_client_config():
    """Helper method to generate Google client config based on app settings"""
    return {
        "web": {
            "client_id": settings.DRIVE_CLIENT_ID,
            "client_secret": settings.DRIVE_CLIENT_SECRET,
            "project_id": settings.DRIVE_API_PROJECT_ID,
            "redirect_uris": [
                urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
            ],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        }
    }
