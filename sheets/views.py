"""HTTP views for sheets app"""
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from rest_framework import status

# NOTE: Due to an unresolved bug (https://github.com/PyCQA/pylint/issues/2108), the
# `google` package (and other packages without an __init__.py file) will break pylint.
# The `disable-all` rules are here until that bug is fixed.
from google_auth_oauthlib.flow import Flow  # pylint: disable-all
from google.auth.exceptions import GoogleAuthError  # pylint: disable-all

from mitxpro.utils import now_in_utc
from sheets.api import get_sheet_metadata_from_type
from sheets.models import GoogleApiAuth, GoogleFileWatch
from sheets.constants import (
    REQUIRED_GOOGLE_API_SCOPES,
    SHEET_TYPE_COUPON_REQUEST,
    SHEET_TYPE_ENROLL_CHANGE,
    SHEET_TYPE_COUPON_ASSIGN,
)
from sheets.utils import generate_google_client_config
from sheets import tasks
from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.coupon_request_api import CouponRequestHandler

log = logging.getLogger(__name__)


@staff_member_required(login_url="login")
def sheets_admin_view(request):
    """Admin view that renders a page that allows a user to begin Google OAuth auth"""
    if not settings.FEATURES.get("COUPON_SHEETS"):
        raise Http404
    existing_api_auth = GoogleApiAuth.objects.first()
    successful_action = request.GET.get("success")
    return render(
        request,
        "admin.html",
        {
            "existing_api_auth": existing_api_auth,
            "auth_completed": successful_action == "auth",
        },
    )


@staff_member_required(login_url="login")
def request_google_auth(request):
    """Admin view to begin Google OAuth auth"""
    if not settings.FEATURES.get("COUPON_SHEETS"):
        raise Http404
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
    if not settings.FEATURES.get("COUPON_SHEETS"):
        raise Http404
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
        google_api_auth, _ = GoogleApiAuth.objects.select_for_update().get_or_create()
        google_api_auth.requesting_user = request.user
        google_api_auth.access_token = credentials.token
        google_api_auth.refresh_token = credentials.refresh_token
        google_api_auth.save()

    return redirect("{}?success=auth".format(reverse("sheets-admin-view")))


@csrf_exempt
def handle_watched_sheet_update(request):
    """
    View that handles requests sent from Google's push notification service when changes are made to the
    a sheet with a file watch applied.
    """
    if not settings.FEATURES.get("COUPON_SHEETS"):
        raise Http404
    channel_id = request.META.get("HTTP_X_GOOG_CHANNEL_ID")
    if not channel_id:
        log.error(
            "Google file watch request received without a Channel ID in the expected header field "
            "(HTTP_X_GOOG_CHANNEL_ID)."
        )
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

    sheet_type = request.GET.get("sheet", SHEET_TYPE_COUPON_REQUEST)
    try:
        sheet_metadata = get_sheet_metadata_from_type(sheet_type)
    except:
        log.error(
            "Unknown sheet type '%s' (passed via 'sheet' query parameter)", sheet_type
        )
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
    qs_file_id = request.GET.get("fileId")
    if sheet_type == SHEET_TYPE_COUPON_ASSIGN and qs_file_id is None:
        log.error(
            "Webhook requests for '%s' sheet received without a 'fileId' parameter",
            sheet_type,
        )
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
    file_id = qs_file_id or sheet_metadata.sheet_file_id

    try:
        with transaction.atomic():
            req_sheet_file_watch = GoogleFileWatch.objects.select_for_update().get(
                file_id=file_id
            )
            req_sheet_file_watch.last_request_received = now_in_utc()
            req_sheet_file_watch.save()
    except GoogleFileWatch.DoesNotExist:
        log.error(
            "Google file watch request for %s received (%s), but no local file watch record exists "
            "in the database.",
            sheet_metadata.sheet_name,
            file_id,
        )
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
    if channel_id != req_sheet_file_watch.channel_id:
        log.warning(
            "Google file watch request for %s received, but the Channel ID does not match the "
            "active file watch channel ID in the app (%s, %s)",
            sheet_metadata.sheet_name,
            channel_id,
            req_sheet_file_watch.channel_id,
        )
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

    if sheet_type == SHEET_TYPE_COUPON_REQUEST:
        tasks.handle_unprocessed_coupon_requests.delay()
    elif sheet_type == SHEET_TYPE_COUPON_ASSIGN:
        tasks.schedule_coupon_assignment_sheet_handling.delay(file_id)
    elif sheet_type == SHEET_TYPE_ENROLL_CHANGE:
        tasks.handle_unprocessed_refund_requests.delay()
        tasks.handle_unprocessed_deferral_requests.delay()

    return HttpResponse(status=status.HTTP_200_OK)
