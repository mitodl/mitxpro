"""Courseware API tests"""
# pylint: disable=redefined-outer-name

from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qsl

import pytest
from oauth2_provider.models import Application, AccessToken
from freezegun import freeze_time
import responses
from rest_framework import status

from courses.factories import CourseRunFactory
from courseware.api import (
    create_edx_user,
    create_edx_auth_token,
    refresh_edx_api_auth,
    get_edx_api_client,
    enroll_in_edx_course_run,
)
from courseware.constants import PLATFORM_EDX
from courseware.exceptions import CoursewareUserCreateError
from courseware.factories import OpenEdxApiAuthFactory
from courseware.models import CoursewareUser, OpenEdxApiAuth
from mitxpro.test_utils import MockResponse
from mitxpro.utils import now_in_utc

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def scenario(settings, mocker):
    """Test data and settings needed for create_edx_user tests"""
    settings.OPENEDX_OAUTH_APP_NAME = "test_app_name"
    settings.OPENEDX_API_BASE_URL = "http://example.com"
    settings.MITXPRO_OAUTH_PROVIDER = "test_provider"
    mocked_post = mocker.patch("courseware.api.requests.post")
    application = Application.objects.create(
        name=settings.OPENEDX_OAUTH_APP_NAME,
        user=None,
        client_type="confidential",
        authorization_grant_type="authorization-code",
        skip_authorization=True,
    )
    return SimpleNamespace(mocked_post=mocked_post, application=application)


def test_create_edx_user(user, settings, scenario):
    """Test that create_edx_user makes a request to create an edX user"""
    scenario.mocked_post.return_value = MockResponse(
        content='{"success": true}', status_code=status.HTTP_200_OK
    )

    create_edx_user(user)

    # An AccessToken should be created during execution
    created_access_token = AccessToken.objects.get(application=scenario.application)
    assert (
        scenario.mocked_post.call_args[0][0]
        == "http://example.com/user_api/v1/account/registration/"
    )
    assert scenario.mocked_post.call_args[1]["data"] == {
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "provider": settings.MITXPRO_OAUTH_PROVIDER,
        "access_token": created_access_token.token,
        "country": "US",
        "honor_code": True,
    }
    assert (
        CoursewareUser.objects.filter(
            user=user, platform=PLATFORM_EDX, has_been_synced=True
        ).exists()
        is True
    )


def test_create_edx_user_conflict(user, scenario):
    """Test that create_edx_user handles a 409 response from the edX API"""
    scenario.mocked_post.return_value = MockResponse(
        content='{"username": "exists"}', status_code=status.HTTP_409_CONFLICT
    )

    with pytest.raises(CoursewareUserCreateError):
        create_edx_user(user)

    assert CoursewareUser.objects.count() == 0


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_create_edx_auth_token(settings, user):
    """Tests create_edx_auth_token makes the expected incantations to create a OpenEdxApiAuth"""
    refresh_token = "abc123"
    access_token = "def456"
    code = "ghi789"
    responses.add(
        responses.GET,
        f"{settings.OPENEDX_API_BASE_URL}/auth/login/mitxpro-oauth2/?auth_entry=login",
        status=status.HTTP_200_OK,
    )
    responses.add(
        responses.GET,
        f"{settings.OPENEDX_API_BASE_URL}/oauth2/authorize",
        headers={
            "Location": f"{settings.SITE_BASE_URL}/login/_private/complete?code={code}"
        },
        status=status.HTTP_302_FOUND,
    )
    responses.add(
        responses.GET,
        f"{settings.SITE_BASE_URL}/login/_private/complete",
        status=status.HTTP_200_OK,
    )
    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/oauth2/access_token",
        json=dict(
            refresh_token=refresh_token, access_token=access_token, expires_in=3600
        ),
        status=status.HTTP_200_OK,
    )

    create_edx_auth_token(user)

    assert len(responses.calls) == 4
    assert dict(parse_qsl(responses.calls[3].request.body)) == dict(
        code=code,
        grant_type="authorization_code",
        client_id=settings.OPENEDX_API_CLIENT_ID,
        client_secret=settings.OPENEDX_API_CLIENT_SECRET,
        redirect_uri=f"{settings.SITE_BASE_URL}/login/_private/complete",
    )

    assert OpenEdxApiAuth.objects.filter(user=user).exists()

    auth = OpenEdxApiAuth.objects.get(user=user)

    assert auth.refresh_token == refresh_token
    assert auth.access_token == access_token
    # plus expires_in, minutes 10 seconds
    assert auth.access_token_expires_on == now_in_utc() + timedelta(
        minutes=59, seconds=50
    )


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_refresh_edx_api_auth(settings):
    """Tests refresh_edx_api_auth makes the expected incantations to create a OpenEdxApiAuth"""
    auth = OpenEdxApiAuthFactory.create(expired=True)
    refresh_token = "abc123"
    access_token = "def456"
    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/oauth2/access_token",
        json=dict(
            refresh_token=refresh_token, access_token=access_token, expires_in=3600
        ),
        status=status.HTTP_200_OK,
    )

    refresh_edx_api_auth(auth.user)

    assert len(responses.calls) == 1
    assert dict(parse_qsl(responses.calls[0].request.body)) == dict(
        refresh_token=auth.refresh_token,
        grant_type="refresh_token",
        client_id=settings.OPENEDX_API_CLIENT_ID,
        client_secret=settings.OPENEDX_API_CLIENT_SECRET,
    )

    auth.refresh_from_db()

    assert auth.refresh_token == refresh_token
    assert auth.access_token == access_token
    # plus expires_in, minutes 10 seconds
    assert auth.access_token_expires_on == now_in_utc() + timedelta(
        minutes=59, seconds=50
    )


def test_get_edx_api_client(mocker, settings, user):
    """Tests that get_edx_api_client returns an EdxApi client"""
    settings.OPENEDX_API_BASE_URL = "http://example.com"
    auth = OpenEdxApiAuthFactory.build(user=user)
    mock_refresh = mocker.patch(
        "courseware.api.refresh_edx_api_auth", return_value=auth
    )
    client = get_edx_api_client(user)
    assert client.credentials["access_token"] == auth.access_token
    assert client.base_url == settings.OPENEDX_API_BASE_URL
    mock_refresh.assert_called_with(user)


def test_enroll_in_edx_course_run(mocker, user):
    """Tests that enroll_in_edx_course_run uses the EdxApi client to enroll in a course run"""
    mock_client = mocker.MagicMock()
    mocker.patch("courseware.api.get_edx_api_client", return_value=mock_client)
    course_run = CourseRunFactory.build()
    enroll_in_edx_course_run(user, course_run)
    mock_client.enrollments.create_audit_student_enrollment.assert_called_with(
        course_run.courseware_id
    )
