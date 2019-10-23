"""HTTP views for sheets app"""
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

# NOTE: Due to an unresolved bug (https://github.com/PyCQA/pylint/issues/2108), the
# `google` package (and other packages without an __init__.py file) will break pylint.
# The `disable-all` rules are here until that bug is fixed.
from google_auth_oauthlib.flow import Flow  # pylint: disable-all
from google.auth.exceptions import GoogleAuthError  # pylint: disable-all

from sheets.models import GoogleApiAuth
from sheets.constants import REQUIRED_GOOGLE_API_SCOPES
from sheets.utils import generate_google_client_config
from sheets import tasks

log = logging.getLogger(__name__)


@staff_member_required(login_url="login")
def google_auth_view(request):
    """Admin view that renders a page that allows a user to begin Google OAuth auth"""
    existing_api_auth = GoogleApiAuth.objects.filter(requesting_user=request.user)
    return render(
        request,
        "google_auth.html",
        {
            "existing_api_auth": existing_api_auth,
            "auth_completed": bool(request.GET.get("success", False)),
        },
    )


@staff_member_required(login_url="login")
def request_google_auth(request):
    """Admin view to begin Google OAuth auth"""
    flow = Flow.from_client_config(
        generate_google_client_config(), scopes=REQUIRED_GOOGLE_API_SCOPES
    )
    flow.redirect_uri = urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["state"] = state
    request.session["code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@csrf_exempt
def complete_google_auth(request):
    """Admin view that handles the redirect from Google after completing Google auth"""
    state = request.session.get("state")
    if not state:
        raise GoogleAuthError(
            "Could not complete Google auth - 'state' was not found in the session"
        )
    flow = Flow.from_client_config(
        generate_google_client_config(), scopes=REQUIRED_GOOGLE_API_SCOPES, state=state
    )
    flow.redirect_uri = urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
    flow.code_verifier = request.session["code_verifier"]
    flow.fetch_token(code=request.GET.get("code"))

    # Store credentials
    credentials = flow.credentials
    with transaction.atomic():
        google_api_auth, _ = GoogleApiAuth.objects.select_for_update().get_or_create(
            requesting_user=request.user
        )
        google_api_auth.access_token = credentials.token
        google_api_auth.refresh_token = credentials.refresh_token
        google_api_auth.save()

    return redirect("{}?success=1".format(reverse("google-auth-view")))


@csrf_exempt
def handle_coupon_request_sheet_update(request):
    """View that handles requests sent from Google's push notification service when a file changes"""
    tasks.handle_unprocessed_coupon_requests.delay()
    return HttpResponse(status=status.HTTP_200_OK)
