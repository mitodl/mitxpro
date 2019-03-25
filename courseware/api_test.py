"""Courseware API tests"""
# pylint: disable=redefined-outer-name

from types import SimpleNamespace
import pytest
from oauth2_provider.models import Application, AccessToken
from rest_framework import status

from courseware.api import create_edx_user
from courseware.constants import PLATFORM_EDX
from courseware.models import CoursewareUser
from mitxpro.test_utils import MockResponse


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


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_create_edx_user_conflict(user, scenario):
    """Test that create_edx_user handles a 409 response from the edX API"""
    scenario.mocked_post.return_value = MockResponse(
        content='{"username": "exists"}', status_code=status.HTTP_409_CONFLICT
    )

    create_edx_user(user)

    assert CoursewareUser.objects.count() == 0
