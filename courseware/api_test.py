"""Courseware API tests"""

import itertools
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode

import pytest
import responses
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from edx_api.enrollments import Enrollments
from freezegun import freeze_time
from oauth2_provider.models import AccessToken, Application
from oauthlib.common import generate_token
from requests.exceptions import HTTPError
from rest_framework import status

from courses.factories import CourseRunEnrollmentFactory, CourseRunFactory
from courseware.api import (
    ACCESS_TOKEN_HEADER_NAME,
    OPENEDX_AUTH_DEFAULT_TTL_IN_SECONDS,
    OpenEdxUser,
    create_edx_auth_token,
    create_edx_user,
    create_oauth_application,
    create_user,
    enroll_in_edx_course_runs,
    get_edx_api_client,
    get_valid_edx_api_auth,
    repair_faulty_courseware_users,
    repair_faulty_edx_user,
    retry_failed_edx_enrollments,
    unenroll_edx_course_run,
    update_edx_user_email,
    update_edx_user_name,
    update_xpro_user_username,
    validate_name_with_edx,
)
from courseware.constants import (
    COURSEWARE_REPAIR_GRACE_PERIOD_MINS,
    EDX_ENROLLMENT_AUDIT_MODE,
    EDX_ENROLLMENT_PRO_MODE,
    PLATFORM_EDX,
    PRO_ENROLL_MODE_ERROR_TEXTS,
)
from courseware.exceptions import (
    CoursewareUserCreateError,
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
    UserNameUpdateFailedException,
    EdxApiRegistrationValidationException,
)
from courseware.factories import CoursewareUserFactory, OpenEdxApiAuthFactory
from courseware.models import CoursewareUser, OpenEdxApiAuth
from mitxpro.test_utils import MockHttpError, MockResponse
from mitxpro.utils import now_in_utc
from users.factories import UserFactory

User = get_user_model()
pytestmark = [pytest.mark.django_db]


@pytest.fixture
def application(settings):
    """Test data and settings needed for create_edx_user tests"""
    settings.OPENEDX_OAUTH_APP_NAME = "test_app_name"
    settings.OPENEDX_API_BASE_URL = "http://example.com"
    settings.MITXPRO_OAUTH_PROVIDER = "test_provider"
    settings.MITXPRO_REGISTRATION_ACCESS_TOKEN = "access_token"  # noqa: S105
    return Application.objects.create(
        name=settings.OPENEDX_OAUTH_APP_NAME,
        user=None,
        client_type="confidential",
        authorization_grant_type="authorization-code",
        skip_authorization=True,
    )


@pytest.fixture
def update_token_response(settings):
    """Mock response for updating an auth token"""
    refresh_token = "abc123"  # noqa: S105
    access_token = "def456"  # noqa: S105

    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/oauth2/access_token",
        json=dict(  # noqa: C408
            refresh_token=refresh_token, access_token=access_token, expires_in=3600
        ),
        status=status.HTTP_200_OK,
    )
    return SimpleNamespace(refresh_token=refresh_token, access_token=access_token)


@pytest.fixture
def update_token_response_error(settings):
    """Mock response for updating an auth token"""
    refresh_token = "abc123"  # noqa: S105
    access_token = "def456"  # noqa: S105

    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/oauth2/access_token",
        json=dict(  # noqa: C408
            refresh_token=refresh_token, access_token=access_token, expires_in=3600
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return SimpleNamespace(refresh_token=refresh_token, access_token=access_token)


def test_validate_name_with_edx_success(mocker):
    """
    Test that validate_name_with_edx successfully returns the validation message
    from edX API when the name is valid.
    """
    name = "Test User"
    mock_response = {"validation_decisions": {"name": "valid name"}}

    mock_client = mocker.MagicMock()
    mock_client.user_info.validate_user_registration.return_value = mock_response
    mocker.patch('mitxpro.courseware.exceptions.get_edx_api_registration_client', return_value=mock_client)

    result = validate_name_with_edx(name)
    assert result == "valid name"
    mock_client.user_info.validate_user_registration.assert_called_once_with(
        data={"name": name}
    )


def test_validate_name_with_edx_failure(mocker):
    """
    Test that validate_name_with_edx raises EdxApiRegistrationValidationException
    when the edX API call fails.
    """
    name = "https://invalid_name"
    mock_client = mocker.MagicMock()
    mock_client.user_info.validate_user_registration.side_effect = Exception("API error")
    mocker.patch('mitxpro.courseware.exceptions.get_edx_api_registration_client', return_value=mock_client)

    with pytest.raises(EdxApiRegistrationValidationException):
        validate_name_with_edx(name)
    mock_client.user_info.validate_user_registration.assert_called_once_with(
        data={"name": name}
    )


@pytest.fixture
def create_token_responses(settings):
    """Mock responses for creating an auth token"""
    refresh_token = "abc123"  # noqa: S105
    access_token = "def456"  # noqa: S105
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
        json=dict(  # noqa: C408
            refresh_token=refresh_token, access_token=access_token, expires_in=3600
        ),
        status=status.HTTP_200_OK,
    )
    return SimpleNamespace(
        refresh_token=refresh_token, access_token=access_token, code=code
    )


def test_create_user(user, mocker):
    """Test that create_user calls the correct APIs"""
    mock_create_edx_user = mocker.patch("courseware.api.create_edx_user")
    mock_create_edx_auth_token = mocker.patch("courseware.api.create_edx_auth_token")
    create_user(user)
    mock_create_edx_user.assert_called_with(user)
    mock_create_edx_auth_token.assert_called_with(user)


@responses.activate
@pytest.mark.parametrize("access_token_count", [0, 1, 3])
def test_create_edx_user(user, settings, application, access_token_count):
    """Test that create_edx_user makes a request to create an edX user"""
    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/user_api/v1/account/registration/",
        json=dict(success=True),  # noqa: C408
        status=status.HTTP_200_OK,
    )

    for _ in range(access_token_count):
        AccessToken.objects.create(
            user=user,
            application=application,
            token=generate_token(),
            expires=now_in_utc() + timedelta(hours=1),
        )

    create_edx_user(user)

    # An AccessToken should be created during execution
    created_access_token = AccessToken.objects.filter(application=application).last()
    assert (
        responses.calls[0].request.headers[ACCESS_TOKEN_HEADER_NAME]
        == settings.MITXPRO_REGISTRATION_ACCESS_TOKEN
    )
    assert dict(parse_qsl(responses.calls[0].request.body)) == {
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "provider": settings.MITXPRO_OAUTH_PROVIDER,
        "access_token": created_access_token.token,
        "country": "US",
        "honor_code": "True",
    }
    assert (
        CoursewareUser.objects.filter(
            user=user, platform=PLATFORM_EDX, has_been_synced=True
        ).exists()
        is True
    )


@responses.activate
@pytest.mark.usefixtures("application")
def test_create_edx_user_conflict(settings, user):
    """Test that create_edx_user handles a 409 response from the edX API"""
    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/user_api/v1/account/registration/",
        json=dict(username="exists"),  # noqa: C408
        status=status.HTTP_409_CONFLICT,
    )
    responses.add(
        responses.GET,
        f"{settings.OPENEDX_API_BASE_URL}/api/user/v1/accounts?{urlencode({'email': user.email})}",
        status=status.HTTP_200_OK,
    )

    with pytest.raises((CoursewareUserCreateError, ImproperlyConfigured)):
        create_edx_user(user)

    assert CoursewareUser.objects.count() == 0


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_create_edx_auth_token(settings, user, create_token_responses):
    """Tests create_edx_auth_token makes the expected incantations to create a OpenEdxApiAuth"""
    create_edx_auth_token(user)

    assert len(responses.calls) == 4
    assert dict(parse_qsl(responses.calls[3].request.body)) == dict(  # noqa: C408
        code=create_token_responses.code,
        grant_type="authorization_code",
        client_id=settings.OPENEDX_API_CLIENT_ID,
        client_secret=settings.OPENEDX_API_CLIENT_SECRET,
        redirect_uri=f"{settings.SITE_BASE_URL}/login/_private/complete",
    )

    assert OpenEdxApiAuth.objects.filter(user=user).exists()

    auth = OpenEdxApiAuth.objects.get(user=user)

    assert auth.refresh_token == create_token_responses.refresh_token
    assert auth.access_token == create_token_responses.access_token
    # plus expires_in, minutes 10 seconds
    assert auth.access_token_expires_on == now_in_utc() + timedelta(
        minutes=59, seconds=50
    )


def test_update_xpro_user_username_successfully(user):
    """Tests update_xpro_user_username updates user successfully"""
    new_username = "new_username"
    assert update_xpro_user_username(user, new_username) is True
    # reload user object from database to get latest value of username
    user.refresh_from_db()
    assert user.username == new_username


def test_update_xpro_user_username_integrity_error(user):
    """Tests update_xpro_user_username raises IntegrityError"""
    old_username = user.username
    new_username = "new_username"
    # create duplicate user with given username
    UserFactory.create(username=new_username)
    with transaction.atomic():
        assert update_xpro_user_username(user, new_username) is False
    # reload user object from database to get latest value of username
    user.refresh_from_db()
    assert user.username == old_username


@responses.activate
def test_update_edx_user_email(settings, user):
    """Tests update_edx_user_email makes the expected incantations to update the user"""
    create_oauth_application()
    responses.add(
        responses.POST,
        f"{settings.OPENEDX_API_BASE_URL}/user_api/v1/account/registration/",
        json=dict(success=True),  # noqa: C408
        status=status.HTTP_200_OK,
    )

    create_edx_user(user)

    courseware_user_qs = CoursewareUser.objects.filter(user=user)
    assert courseware_user_qs.exists()
    assert courseware_user_qs.first().user.email != "abc@example.com"

    user.email = "abc@example.com"
    user.save()

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

    update_edx_user_email(user)

    assert len(responses.calls) == 4
    assert CoursewareUser.objects.get(user=user).user.email == "abc@example.com"


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_get_valid_edx_api_auth_unexpired():
    """Tests get_valid_edx_api_auth returns the current record if it is valid long enough"""
    auth = OpenEdxApiAuthFactory.create()

    updated_auth = get_valid_edx_api_auth(auth.user)

    assert updated_auth is not None
    assert updated_auth.refresh_token == auth.refresh_token
    assert updated_auth.access_token == auth.access_token
    assert updated_auth.access_token_expires_on == auth.access_token_expires_on


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_get_valid_edx_api_auth_expired(settings, update_token_response):
    """Tests get_valid_edx_api_auth fetches and updates the auth credentials if expired"""
    auth = OpenEdxApiAuthFactory.create(expired=True)

    updated_auth = get_valid_edx_api_auth(auth.user)

    assert updated_auth is not None
    assert len(responses.calls) == 1
    assert dict(parse_qsl(responses.calls[0].request.body)) == dict(  # noqa: C408
        refresh_token=auth.refresh_token,
        grant_type="refresh_token",
        client_id=settings.OPENEDX_API_CLIENT_ID,
        client_secret=settings.OPENEDX_API_CLIENT_SECRET,
    )

    assert updated_auth.refresh_token == update_token_response.refresh_token
    assert updated_auth.access_token == update_token_response.access_token
    # plus expires_in, minutes 10 seconds
    assert updated_auth.access_token_expires_on == now_in_utc() + timedelta(
        minutes=59, seconds=50
    )


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_get_valid_edx_api_auth_expired_and_broken(
    settings,
    update_token_response_error,
    create_token_responses,
):
    """Tests get_valid_edx_api_auth fetches and creates new auth credentials if expired/broken"""
    auth = OpenEdxApiAuthFactory.create(expired=True)

    updated_auth = get_valid_edx_api_auth(auth.user)

    assert updated_auth is not None
    assert len(responses.calls) == 5
    assert dict(parse_qsl(responses.calls[0].request.body)) == dict(  # noqa: C408
        refresh_token=auth.refresh_token,
        grant_type="refresh_token",
        client_id=settings.OPENEDX_API_CLIENT_ID,
        client_secret=settings.OPENEDX_API_CLIENT_SECRET,
    )

    assert updated_auth.refresh_token == create_token_responses.refresh_token
    assert updated_auth.access_token == create_token_responses.access_token
    # plus expires_in, minutes 10 seconds
    assert updated_auth.access_token_expires_on == now_in_utc() + timedelta(
        minutes=59, seconds=50
    )


@responses.activate
@freeze_time("2019-03-24 11:50:36")
def test_get_valid_edx_api_auth_deleted(create_token_responses):
    """Tests get_valid_edx_api_auth creates the auth credentials if they don't exist"""
    user = UserFactory.create()

    assert OpenEdxApiAuth.objects.filter(user=user).first() is None

    updated_auth = get_valid_edx_api_auth(user)

    assert updated_auth is not None
    assert len(responses.calls) == 4

    assert updated_auth.refresh_token == create_token_responses.refresh_token
    assert updated_auth.access_token == create_token_responses.access_token
    assert OpenEdxApiAuth.objects.filter(user=user).exists()


def test_get_edx_api_client(mocker, settings, user):
    """Tests that get_edx_api_client returns an EdxApi client"""
    settings.OPENEDX_API_BASE_URL = "http://example.com"
    auth = OpenEdxApiAuthFactory.build(user=user)
    mock_refresh = mocker.patch(
        "courseware.api.get_valid_edx_api_auth", return_value=auth
    )
    client = get_edx_api_client(user)
    assert client.credentials["access_token"] == auth.access_token
    assert client.base_url == settings.OPENEDX_API_BASE_URL
    mock_refresh.assert_called_with(
        user, ttl_in_seconds=OPENEDX_AUTH_DEFAULT_TTL_IN_SECONDS
    )


def test_enroll_in_edx_course_runs(mocker, user):
    """Tests that enroll_in_edx_course_runs uses the EdxApi client to enroll in course runs"""
    mock_client = mocker.MagicMock()
    enroll_return_values = ["result1", "result2"]
    mock_client.enrollments.create_student_enrollment = mocker.Mock(
        side_effect=enroll_return_values
    )
    mocker.patch("courseware.api.get_edx_api_service_client", return_value=mock_client)
    course_runs = CourseRunFactory.build_batch(2)
    enroll_results = enroll_in_edx_course_runs(
        user,
        course_runs,
    )
    expected_username = user.username
    mock_client.enrollments.create_student_enrollment.assert_any_call(
        course_runs[0].courseware_id,
        mode=EDX_ENROLLMENT_PRO_MODE,
        username=expected_username,
        force_enrollment=True,
    )
    mock_client.enrollments.create_student_enrollment.assert_any_call(
        course_runs[1].courseware_id,
        mode=EDX_ENROLLMENT_PRO_MODE,
        username=expected_username,
        force_enrollment=True,
    )
    assert enroll_results == enroll_return_values


@pytest.mark.parametrize("error_text", PRO_ENROLL_MODE_ERROR_TEXTS)
def test_enroll_in_edx_course_runs_audit(mocker, user, error_text):
    """Tests that enroll_in_edx_course_runs fails over to attempting enrollment with 'audit' mode"""
    mock_client = mocker.MagicMock()
    pro_enrollment_response = MockResponse({"message": error_text})
    audit_result = {"good": "result"}
    mock_client.enrollments.create_student_enrollment = mocker.Mock(
        side_effect=[HTTPError(response=pro_enrollment_response), audit_result]
    )
    patched_log_error = mocker.patch("courseware.api.log.error")
    mocker.patch("courseware.api.get_edx_api_service_client", return_value=mock_client)

    course_run = CourseRunFactory.build()
    results = enroll_in_edx_course_runs(user, [course_run])
    assert mock_client.enrollments.create_student_enrollment.call_count == 2
    mock_client.enrollments.create_student_enrollment.assert_any_call(
        course_run.courseware_id,
        mode=EDX_ENROLLMENT_PRO_MODE,
        username=user.username,
        force_enrollment=True,
    )
    mock_client.enrollments.create_student_enrollment.assert_any_call(
        course_run.courseware_id,
        mode=EDX_ENROLLMENT_AUDIT_MODE,
        username=user.username,
        force_enrollment=True,
    )
    assert results == [audit_result]
    patched_log_error.assert_called_once()


def test_enroll_pro_api_fail(mocker, user):
    """
    Tests that enroll_in_edx_course_runs raises an EdxApiEnrollErrorException if the request fails
    for some reason besides an enrollment mode error
    """
    mock_client = mocker.MagicMock()
    pro_enrollment_response = MockResponse({"message": "no dice"}, status_code=401)
    mock_client.enrollments.create_student_enrollment = mocker.Mock(
        side_effect=HTTPError(response=pro_enrollment_response)
    )
    mocker.patch("courseware.api.get_edx_api_service_client", return_value=mock_client)
    course_run = CourseRunFactory.build()

    with pytest.raises(EdxApiEnrollErrorException):
        enroll_in_edx_course_runs(user, [course_run])


def test_enroll_pro_unknown_fail(mocker, user, settings):
    """
    Tests that enroll_in_edx_course_runs raises an UnknownEdxApiEnrollException if an unexpected exception
    is encountered
    """
    mock_client = mocker.MagicMock()
    mock_client.enrollments.create_student_enrollment = mocker.Mock(
        side_effect=ValueError("Unexpected error")
    )
    mocker.patch("courseware.api.get_edx_api_client", return_value=mock_client)
    course_run = CourseRunFactory.build()
    settings.OPENEDX_SERVICE_WORKER_API_TOKEN = "mock_api_token"  # noqa: S105

    with pytest.raises(UnknownEdxApiEnrollException):
        enroll_in_edx_course_runs(user, [course_run])


@pytest.mark.parametrize("exception_raised", [Exception("An error happened"), None])
def test_retry_failed_edx_enrollments(mocker, exception_raised):
    """
    Tests that retry_failed_edx_enrollments loops through enrollments that failed in edX
    and attempts to enroll them again
    """
    with freeze_time(now_in_utc() - timedelta(days=1)):
        failed_enrollments = CourseRunEnrollmentFactory.create_batch(
            3, edx_enrolled=False, user__is_active=True
        )
        CourseRunEnrollmentFactory.create(edx_enrolled=False, user__is_active=False)
    patched_enroll_in_edx = mocker.patch(
        "courseware.api.enroll_in_edx_course_runs",
        side_effect=[None, exception_raised or None, None],
    )
    patched_log_exception = mocker.patch("courseware.api.log.exception")
    successful_enrollments = retry_failed_edx_enrollments()

    assert patched_enroll_in_edx.call_count == len(failed_enrollments)
    assert len(successful_enrollments) == (3 if exception_raised is None else 2)
    assert patched_log_exception.called == bool(exception_raised)
    if exception_raised:
        failed_enroll_user, failed_enroll_runs = patched_enroll_in_edx.call_args_list[
            1
        ][0]
        expected_successful_enrollments = [
            e
            for e in failed_enrollments
            if e.user != failed_enroll_user and e.run != failed_enroll_runs[0]
        ]
        assert {e.id for e in successful_enrollments} == {
            e.id for e in expected_successful_enrollments
        }


@pytest.mark.parametrize(
    "mode", [EDX_ENROLLMENT_PRO_MODE, EDX_ENROLLMENT_AUDIT_MODE, "other"]
)
@pytest.mark.parametrize(
    "edx_enrollment_exists, is_active",  # noqa: PT006
    [[False, False], [True, True], [True, False]],  # noqa: PT007
)
def test_retry_failed_edx_enrollments_exists(
    mocker, edx_enrollment_exists, is_active, mode
):
    """
    Tests that retry_failed_edx_enrollments loops through enrollments that failed in edX
    and attempts to enroll them again
    """
    is_valid_mode = mode in [EDX_ENROLLMENT_PRO_MODE, EDX_ENROLLMENT_AUDIT_MODE]
    with freeze_time(now_in_utc() - timedelta(days=1)):
        failed_enrollment = CourseRunEnrollmentFactory.create(
            edx_enrolled=False, user__is_active=True
        )
        CourseRunEnrollmentFactory.create(edx_enrolled=False, user__is_active=False)
    patched_enroll_in_edx = mocker.patch(
        "courseware.api.enroll_in_edx_course_runs",
        side_effect=EdxApiEnrollErrorException(
            failed_enrollment.user, failed_enrollment.run, MockHttpError()
        ),
    )
    edx_enrollments = [
        {
            "is_active": is_active,
            "course_details": {"course_id": failed_enrollment.run.courseware_id},
            "mode": mode,
        }
        if edx_enrollment_exists
        else {"foo": "bar"}
    ]
    mock_edx_client = mocker.patch("courseware.api.get_edx_api_client", autospec=True)
    mock_edx_client.return_value.enrollments.get_student_enrollments.return_value = (
        Enrollments(edx_enrollments)
    )

    patched_log = mocker.patch("courseware.api.log")
    successful_enrollments = retry_failed_edx_enrollments()

    assert patched_enroll_in_edx.call_count == 1
    assert len(successful_enrollments) == (
        1 if edx_enrollment_exists and is_active and is_valid_mode else 0
    )
    assert patched_log.exception.called == bool(
        not edx_enrollment_exists or not is_active or not is_valid_mode
    )
    assert patched_log.warning.called == bool(
        edx_enrollment_exists and is_active and is_valid_mode
    )
    failed_enrollment.refresh_from_db()
    assert failed_enrollment.edx_enrolled is (
        edx_enrollment_exists and is_active and is_valid_mode
    )


def test_retry_failed_enroll_grace_period(mocker):
    """
    Tests that retry_failed_edx_enrollments does not attempt to repair any enrollments that were recently created
    """
    now = now_in_utc()
    with freeze_time(now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS - 1)):
        CourseRunEnrollmentFactory.create(edx_enrolled=False, user__is_active=True)
    with freeze_time(now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS + 1)):
        older_enrollment = CourseRunEnrollmentFactory.create(
            edx_enrolled=False, user__is_active=True
        )
    patched_enroll_in_edx = mocker.patch("courseware.api.enroll_in_edx_course_runs")
    successful_enrollments = retry_failed_edx_enrollments()

    assert successful_enrollments == [older_enrollment]
    patched_enroll_in_edx.assert_called_once_with(
        older_enrollment.user, [older_enrollment.run]
    )


@pytest.mark.parametrize(
    "no_courseware_user,no_edx_auth",  # noqa: PT006
    itertools.product([True, False], [True, False]),
)
def test_repair_faulty_edx_user(mocker, user, no_courseware_user, no_edx_auth):
    """
    Tests that repair_faulty_edx_user creates CoursewareUser/OpenEdxApiAuth objects as necessary and
    returns flags that indicate what was created
    """
    patched_create_edx_user = mocker.patch("courseware.api.create_edx_user")
    patched_create_edx_auth_token = mocker.patch("courseware.api.create_edx_auth_token")
    courseware_user = CoursewareUserFactory.create(user=user)
    patched_find_object = mocker.patch(
        "courseware.api.find_object_with_matching_attr",
        return_value=None if no_courseware_user else courseware_user,
    )
    openedx_api_auth = None if no_edx_auth else OpenEdxApiAuthFactory.build()
    user.openedx_api_auth = openedx_api_auth

    created_user, created_auth_token = repair_faulty_edx_user(user)
    patched_find_object.assert_called_once()
    assert patched_create_edx_user.called is no_courseware_user
    assert patched_create_edx_auth_token.called is no_edx_auth
    assert created_user is no_courseware_user
    assert created_auth_token is no_edx_auth


@pytest.mark.parametrize("exception_raised", [MockHttpError, Exception, None])
def test_repair_faulty_courseware_users(mocker, exception_raised):
    """
    Tests that repair_faulty_courseware_users loops through all incorrectly configured Users, attempts to repair
    them, and continues iterating through the Users if an exception is raised
    """
    with freeze_time(now_in_utc() - timedelta(days=1)):
        users = UserFactory.create_batch(3)
    user_count = len(users)
    patched_log_exception = mocker.patch("courseware.api.log.exception")
    patched_faulty_user_qset = mocker.patch(
        "users.models.FaultyCoursewareUserManager.get_queryset",
        return_value=User.objects.all(),
    )
    patched_repair_user = mocker.patch(
        "courseware.api.repair_faulty_edx_user",
        side_effect=[
            (True, True),
            # Function should continue executing if an exception is thrown
            exception_raised or (True, True),
            (True, True),
        ],
    )
    repaired_users = repair_faulty_courseware_users()

    patched_faulty_user_qset.assert_called_once()
    assert patched_repair_user.call_count == user_count
    assert len(repaired_users) == (3 if exception_raised is None else 2)
    assert patched_log_exception.called == bool(exception_raised)
    if exception_raised:
        failed_user = patched_repair_user.call_args_list[1][0]
        expected_repaired_users = [user for user in users if user != failed_user]
        assert {u.id for u in users} == {u.id for u in expected_repaired_users}


def test_retry_users_grace_period(mocker):
    """
    Tests that repair_faulty_courseware_users does not attempt to repair any users that were recently created
    """
    now = now_in_utc()
    with freeze_time(now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS - 1)):
        UserFactory.create()
    with freeze_time(now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS + 1)):
        user_to_repair = UserFactory.create()
    patched_faulty_user_qset = mocker.patch(
        "users.models.FaultyCoursewareUserManager.get_queryset",
        return_value=User.objects.all(),
    )
    patched_repair_user = mocker.patch(
        "courseware.api.repair_faulty_edx_user", return_value=(True, True)
    )
    repaired_users = repair_faulty_courseware_users()

    assert repaired_users == [user_to_repair]
    patched_faulty_user_qset.assert_called_once()
    patched_repair_user.assert_called_once_with(user_to_repair)


def test_unenroll_edx_course_run(mocker):
    """Tests that unenroll_edx_course_run makes a call to unenroll in edX via the API client"""
    mock_client = mocker.MagicMock()
    run_enrollment = CourseRunEnrollmentFactory.create(edx_enrolled=True)
    courseware_id = run_enrollment.run.courseware_id
    username = run_enrollment.user.username
    enroll_return_value = mocker.Mock(
        json={"course_id": courseware_id, "user": username}
    )
    mock_client.enrollments.deactivate_enrollment = mocker.Mock(
        return_value=enroll_return_value
    )
    mocker.patch("courseware.api.get_edx_api_service_client", return_value=mock_client)
    deactivated_enrollment = unenroll_edx_course_run(run_enrollment)

    mock_client.enrollments.deactivate_enrollment.assert_called_once_with(
        courseware_id, username=username
    )
    assert deactivated_enrollment == enroll_return_value


@pytest.mark.parametrize(
    "client_exception_raised,expected_exception",  # noqa: PT006
    [
        [MockHttpError, EdxApiEnrollErrorException],  # noqa: PT007
        [ValueError, UnknownEdxApiEnrollException],  # noqa: PT007
        [Exception, UnknownEdxApiEnrollException],  # noqa: PT007
    ],
)
def test_unenroll_edx_course_run_failure(
    mocker, client_exception_raised, expected_exception
):
    """Tests that unenroll_edx_course_run translates exceptions raised by the API client"""
    run_enrollment = CourseRunEnrollmentFactory.create(edx_enrolled=True)
    mock_client = mocker.MagicMock()
    mock_client.enrollments.deactivate_enrollment = mocker.Mock(
        side_effect=client_exception_raised
    )
    mocker.patch("courseware.api.get_edx_api_service_client", return_value=mock_client)
    with pytest.raises(expected_exception):
        unenroll_edx_course_run(run_enrollment)


def test_update_user_edx_name(mocker, user):
    """Test that update_edx_user makes a call to update update_user_name in edX via API client"""
    user.name = "Test Name"
    mock_client = mocker.MagicMock()
    update_name_return_value = mocker.Mock(
        json={"name": user.name, "username": user.username, "email": user.email}
    )
    mock_client.user_info.update_user_name = mocker.Mock(
        return_value=update_name_return_value
    )
    mocker.patch("courseware.api.get_edx_api_client", return_value=mock_client)
    updated_user = update_edx_user_name(user)
    mock_client.user_info.update_user_name.assert_called_once_with(
        user.username, user.name
    )
    assert update_name_return_value == updated_user


@pytest.mark.parametrize(
    "client_exception_raised,expected_exception",  # noqa: PT006
    [
        [MockHttpError, UserNameUpdateFailedException],  # noqa: PT007
        [ValueError, UserNameUpdateFailedException],  # noqa: PT007
        [Exception, UserNameUpdateFailedException],  # noqa: PT007
    ],
)
def test_update_edx_user_name_failure(
    mocker, client_exception_raised, expected_exception, user
):
    """Tests that update_edx_user_name translates exceptions raised by the API client"""
    mock_client = mocker.MagicMock()
    mock_client.user_info.update_user_name = mocker.Mock(
        side_effect=client_exception_raised
    )
    mocker.patch("courseware.api.get_edx_api_client", return_value=mock_client)
    with pytest.raises(expected_exception):
        update_edx_user_name(user)


@pytest.fixture
def test_user():
    """
    Fixture that creates a `User` with username="test_user" object for testing.
    """
    return UserFactory.create(username="test_user")


@pytest.fixture
def openedx_data():
    """
    Fixture providing a sample dictionary with OpenEdx user data.
    """
    return {"username": "test_user"}


@pytest.fixture
def open_edx_user(test_user, openedx_data):
    """
    Fixture that creates an `OpenEdxUser` object for testing.
    """
    return OpenEdxUser(user=test_user, openedx_data=openedx_data)


def test_is_username_match_returns_true(open_edx_user):
    """
    Test that `is_username_match()` returns True when the username of the `User` object matches
    the 'username' field in `openedx_data`.
    """
    assert open_edx_user.is_username_match() is True


def test_is_username_match_returns_false(test_user, openedx_data):
    """
    Test that `is_username_match()` returns False when the username of the `User` object does not
    match the 'username' field in `openedx_data`.
    """
    openedx_data["username"] = "wrong_username"
    open_edx_user = OpenEdxUser(user=test_user, openedx_data=openedx_data)
    assert open_edx_user.is_username_match() is False


def test_is_username_match_with_mock(mocker, openedx_data):
    """
    Test that `is_username_match()` works correctly when the `user` argument is replaced by a
    `MagicMock` object with a different username.
    """
    magic_mock_user = mocker.MagicMock(spec=User)
    open_edx_user = OpenEdxUser(user=magic_mock_user, openedx_data=openedx_data)
    assert not open_edx_user.is_username_match()


def test_is_username_match_with_empty_openedx_data(test_user):
    """
    Test that `is_username_match()` returns False when `openedx_data` is an empty dictionary.
    """
    open_edx_user = OpenEdxUser(user=test_user, openedx_data={})
    assert open_edx_user.is_username_match() is False


def test_is_username_match_with_missing_openedx_data(test_user):
    """
    Test that `is_username_match()` returns False when `openedx_data` does not contain a 'username'
    field.
    """
    open_edx_user = OpenEdxUser(
        user=test_user, openedx_data={"email": "test@example.com"}
    )
    assert open_edx_user.is_username_match() is False
