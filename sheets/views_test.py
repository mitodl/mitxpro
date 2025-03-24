"""Tests for sheets app views"""

import pytest
from django.test.client import Client, RequestFactory
from django.urls import reverse
from pytest_lazy_fixtures import lf as lazy
from rest_framework import status

from mitxpro.test_utils import set_request_session
from sheets.exceptions import CouponAssignmentError
from sheets.factories import GoogleApiAuthFactory, GoogleFileWatchFactory
from sheets.models import GoogleApiAuth
from sheets.views import complete_google_auth


@pytest.fixture
def google_api_auth(user):
    """Fixture that creates a google auth object"""
    return GoogleApiAuthFactory.create(requesting_user=user)


@pytest.mark.parametrize("url_name", ["sheets-admin-view", "request-google-auth"])
def test_staff_only_views(user_client, url_name):
    """Sheets auth views should be staff-only"""
    resp = user_client.get(reverse(url_name))
    assert resp.status_code == status.HTTP_302_FOUND


def test_request_auth(mocker, settings, staff_client):
    """
    View that starts Google auth should set session variables and redirect to the
    expected Google auth page
    """
    settings.SITE_BASE_URL = "http://example.com"
    fake_redirect_url = "/"
    fake_state = "some-state"
    fake_code_verifier = "some-code-verifier"
    flow_mock = mocker.Mock(
        authorization_url=mocker.Mock(return_value=(fake_redirect_url, fake_state)),
        code_verifier=fake_code_verifier,
    )
    patched_flow = mocker.patch(
        "sheets.views.Flow", from_client_config=mocker.Mock(return_value=flow_mock)
    )

    resp = staff_client.get(reverse("request-google-auth"), follow=False)
    patched_flow.from_client_config.assert_called_once()
    flow_mock.authorization_url.assert_called_once_with(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    assert resp.status_code == status.HTTP_302_FOUND
    assert resp.url == fake_redirect_url
    assert staff_client.session["state"] == fake_state
    assert staff_client.session["code_verifier"] == fake_code_verifier


@pytest.mark.parametrize("existing_auth", [lazy("google_api_auth"), None])
@pytest.mark.django_db
def test_complete_auth(mocker, settings, user, existing_auth):
    """
    View that handles Google auth completion should fetch a token and save/update a
    GoogleApiAuth object
    """
    settings.SITE_BASE_URL = "http://example.com"
    access_token = "access-token-123"  # noqa: S105
    refresh_token = "refresh-token-123"  # noqa: S105
    code = "auth-code"
    flow_mock = mocker.Mock(
        credentials=mocker.Mock(token=access_token, refresh_token=refresh_token)
    )
    patched_flow = mocker.patch(
        "sheets.views.Flow", from_client_config=mocker.Mock(return_value=flow_mock)
    )
    auth_complete_url = "{}?code={}".format(reverse("complete-google-auth"), code)
    # There was an issue with setting session variables in a normal Django test client,
    # so RequestFactory is being used to test the view directly.
    request = set_request_session(
        RequestFactory().get(auth_complete_url),
        session_dict={"state": "some-state", "code_verifier": "some-verifier"},
        mocker=mocker,
    )
    request.user = user

    response = complete_google_auth(request)
    patched_flow.from_client_config.assert_called_once()
    patched_flow_obj = patched_flow.from_client_config.return_value
    assert (
        patched_flow_obj.redirect_uri == "http://example.com/api/sheets/auth-complete/"
    )
    assert patched_flow_obj.code_verifier == "some-verifier"
    patched_flow_obj.fetch_token.assert_called_once_with(code=code)
    assert GoogleApiAuth.objects.count() == 1
    assert (
        GoogleApiAuth.objects.filter(
            requesting_user=user, access_token=access_token, refresh_token=refresh_token
        ).exists()
        is True
    )
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url.startswith(reverse("sheets-admin-view"))


@pytest.mark.django_db
def test_handle_coupon_request_sheet_update(mocker, settings):
    """
    View that handles push notifications for file changes in Google should call a task to
    create coupons and write the results to the necessary Sheets.
    """
    settings.COUPON_REQUEST_SHEET_ID = "abc123"
    GoogleFileWatchFactory.create(
        file_id=settings.COUPON_REQUEST_SHEET_ID, channel_id="file-watch-channel"
    )
    patched_tasks = mocker.patch("sheets.views.tasks")
    client = Client()
    client.get(
        reverse("handle-watched-sheet-update"),
        HTTP_X_GOOG_CHANNEL_ID="file-watch-channel",
    )
    patched_tasks.handle_unprocessed_coupon_requests.delay.assert_called_once()


@pytest.mark.parametrize(
    "request_data, mock_return, expected_status, expected_response",
    [
        # Valid request
        (
            {"sheet_identifier_type": "id", "sheet_identifier_value": "valid_sheet", "force": False},
            ("Spreadsheet1", 10, 5, "bulk_id_123"),
            status.HTTP_200_OK,
            {
                "message": "Successfully processed coupon assignment sheet (Spreadsheet1).",
                "num_created": 10,
                "num_removed": 5,
                "bulk_assignment_id": "bulk_id_123",
            },
        ),
        # Missing required fields
        (
            {"sheet_identifier_type": "id"},
            None,
            status.HTTP_400_BAD_REQUEST,
            {"error": "Both 'sheet_identifier_type' and 'sheet_value' are required."},
        ),
        # CouponAssignmentError exception
        (
            {"sheet_identifier_type": "id", "sheet_identifier_value": "invalid_sheet"},
            CouponAssignmentError("Invalid sheet"),
            status.HTTP_400_BAD_REQUEST,
            {"error": "Invalid sheet"},
        ),
        # Unexpected exception
        (
            {"sheet_identifier_type": "id", "sheet_identifier_value": "error_sheet"},
            Exception("Unexpected error"),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"error": "An error occurred while processing the coupon sheet."},
        ),
    ],
)
def test_process_coupon_sheet_assignment(mocker, admin_drf_client, request_data, mock_return, expected_status, expected_response):
    """Test the ProcessCouponSheetAssignmentView post method"""
    url = reverse("process-coupon-sheet-assignment")
    if isinstance(mock_return, Exception):
        mocker.patch("sheets.views.assign_coupons_from_spreadsheet", side_effect=mock_return)
    else:
        mocker.patch("sheets.views.assign_coupons_from_spreadsheet", return_value=mock_return)
    response = admin_drf_client.post(url, request_data, format="json")
    assert response.status_code == expected_status
    assert response.json() == expected_response
