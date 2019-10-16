"""HTTP views for sheets app """
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from rest_framework import status
from google_auth_oauthlib.flow import Flow

from sheets.api import CouponRequestHandler
from sheets.models import GoogleApiAuth
from sheets.constants import (
    REQUIRED_GOOGLE_API_SCOPES,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
)

log = logging.getLogger(__name__)


@staff_member_required
def google_auth_view(request):
    """Admin view to begin Google OAuth authentication"""
    existing_api_auth = GoogleApiAuth.objects.filter(user=request.user)
    return render(
        request,
        "google_auth.html",
        {
            "existing_api_auth": existing_api_auth,
            "auth_completed": bool(request.GET.get("success", False))
        }
    )


def generate_google_client_config():
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


@staff_member_required
def request_google_auth(request):
    flow = Flow.from_client_config(
        generate_google_client_config(),
        scopes=REQUIRED_GOOGLE_API_SCOPES
    )
    flow.redirect_uri = urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["state"] = state
    request.session["code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@csrf_exempt
def complete_google_auth(request):
    state = request.session["state"]

    flow = Flow.from_client_config(
        generate_google_client_config(),
        scopes=REQUIRED_GOOGLE_API_SCOPES,
        state=state
    )
    flow.redirect_uri = urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
    flow.code_verifier = request.session["code_verifier"]

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    flow.fetch_token(code=request.GET.get("code"))

    # Store credentials
    credentials = flow.credentials
    with transaction.atomic():
        google_api_auth, _ = GoogleApiAuth.objects.select_for_update().get_or_create(
            user=request.user
        )
        google_api_auth.access_token = credentials.token
        google_api_auth.refresh_token = credentials.refresh_token
        google_api_auth.id_token = credentials.id_token
        google_api_auth.save()

    return redirect("{}?success=1".format(reverse("google-auth-view")))


@csrf_exempt
def handle_coupon_request_sheet_update(request):
    log.info("Received push notification for update to coupon request sheet")
    coupon_request_handler = CouponRequestHandler()
    processed_requests = coupon_request_handler.create_coupons_from_sheet()
    coupon_request_handler.write_results_to_sheets(processed_requests)
    return HttpResponse(status=status.HTTP_200_OK)
