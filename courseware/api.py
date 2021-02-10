"""Courseware API functions"""
import logging
from datetime import timedelta
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from requests.exceptions import HTTPError
from rest_framework import status

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import reverse
from oauth2_provider.models import Application, AccessToken
from oauthlib.common import generate_token
from edx_api.client import EdxApi

from authentication import api as auth_api
from courses.models import CourseRunEnrollment
from courseware.exceptions import (
    OpenEdXOAuth2Error,
    CoursewareUserCreateError,
    NoEdxApiAuthError,
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
    UserNameUpdateFailedException,
)
from courseware.models import CoursewareUser, OpenEdxApiAuth
from courseware.constants import (
    PLATFORM_EDX,
    EDX_ENROLLMENT_PRO_MODE,
    EDX_ENROLLMENT_AUDIT_MODE,
    PRO_ENROLL_MODE_ERROR_TEXTS,
    COURSEWARE_REPAIR_GRACE_PERIOD_MINS,
)
from courseware.utils import edx_url
from mitxpro.utils import (
    now_in_utc,
    find_object_with_matching_attr,
    get_error_response_summary,
    is_json_response,
)

log = logging.getLogger(__name__)
User = get_user_model()

OPENEDX_REGISTER_USER_PATH = "/user_api/v1/account/registration/"
OPENEDX_REQUEST_DEFAULTS = dict(country="US", honor_code=True)

OPENEDX_SOCIAL_LOGIN_XPRO_PATH = "/auth/login/mitxpro-oauth2/?auth_entry=login"
OPENEDX_OAUTH2_AUTHORIZE_PATH = "/oauth2/authorize"
OPENEDX_OAUTH2_ACCESS_TOKEN_PATH = "/oauth2/access_token"
OPENEDX_OAUTH2_SCOPES = ["read", "write"]
OPENEDX_OAUTH2_ACCESS_TOKEN_PARAM = "code"
OPENEDX_OAUTH2_ACCESS_TOKEN_EXPIRY_MARGIN_SECONDS = 10

OPENEDX_AUTH_DEFAULT_TTL_IN_SECONDS = 60
OPENEDX_AUTH_MAX_TTL_IN_SECONDS = 60 * 60

ACCESS_TOKEN_HEADER_NAME = "X-Access-Token"


def create_user(user):
    """
    Creates a user and any related artifacts in the courseware

    Args:
        user (user.models.User): the application user
    """
    create_edx_user(user)
    create_edx_auth_token(user)


def create_edx_user(user):
    """
    Makes a request to create an equivalent user in Open edX

    Args:
        user (user.models.User): the application user
    """
    application = Application.objects.get(name=settings.OPENEDX_OAUTH_APP_NAME)
    expiry_date = now_in_utc() + timedelta(hours=settings.OPENEDX_TOKEN_EXPIRES_HOURS)
    access_token = AccessToken.objects.create(
        user=user, application=application, token=generate_token(), expires=expiry_date
    )

    with transaction.atomic():
        _, created = CoursewareUser.objects.select_for_update().get_or_create(
            user=user, platform=PLATFORM_EDX
        )

        if not created:
            return

        # a non-200 status here will ensure we rollback creation of the CoursewareUser and try again
        req_session = requests.Session()
        if settings.MITXPRO_REGISTRATION_ACCESS_TOKEN is not None:
            req_session.headers.update(
                {ACCESS_TOKEN_HEADER_NAME: settings.MITXPRO_REGISTRATION_ACCESS_TOKEN}
            )
        resp = req_session.post(
            edx_url(OPENEDX_REGISTER_USER_PATH),
            data=dict(
                username=user.username,
                email=user.email,
                name=user.name,
                provider=settings.MITXPRO_OAUTH_PROVIDER,
                access_token=access_token.token,
                **OPENEDX_REQUEST_DEFAULTS,
            ),
        )
        # edX responds with 200 on success, not 201
        if resp.status_code != status.HTTP_200_OK:
            raise CoursewareUserCreateError(
                f"Error creating Open edX user. {get_error_response_summary(resp)}"
            )


@transaction.atomic
def create_edx_auth_token(user):
    """
    Creates refresh token for LMS for the user

    Args:
        user(user.models.User): the user to create the record for

    Returns:
        courseware.models.OpenEdXAuth: auth model with refresh_token populated
    """

    # In order to acquire auth tokens from Open edX we need to perform the following steps:
    #
    # 1. Create a persistent session so that state is retained like a browser
    # 2. Initialize a session cookie for xPro, this emulates a user login
    # 3. Initiate an Open edX login, delegates to xPro using the session cookie
    # 4. Initiate an Open edX OAuth2 authorization for xPro
    # 5. Redirects back to xPro with the access token
    # 6. Redeem access token for a refresh/access token pair

    # ensure only we can update this for the duration of the
    auth, _ = OpenEdxApiAuth.objects.select_for_update().get_or_create(user=user)

    # we locked on the previous operation and something else populated these values
    if auth.refresh_token and auth.access_token:
        return auth

    # Step 1
    with requests.Session() as req_session:
        # Step 2
        django_session = auth_api.create_user_session(user)
        session_cookie = requests.cookies.create_cookie(
            name=settings.SESSION_COOKIE_NAME,
            domain=urlparse(settings.SITE_BASE_URL).hostname,
            path=settings.SESSION_COOKIE_PATH,
            value=django_session.session_key,
        )
        req_session.cookies.set_cookie(session_cookie)

        # Step 3
        url = edx_url(OPENEDX_SOCIAL_LOGIN_XPRO_PATH)
        resp = req_session.get(url)
        resp.raise_for_status()

        # Step 4
        redirect_uri = urljoin(
            settings.SITE_BASE_URL, reverse("openedx-private-oauth-complete")
        )
        url = edx_url(OPENEDX_OAUTH2_AUTHORIZE_PATH)
        params = dict(
            client_id=settings.OPENEDX_API_CLIENT_ID,
            scope=" ".join(OPENEDX_OAUTH2_SCOPES),
            redirect_uri=redirect_uri,
            response_type="code",
        )
        resp = req_session.get(url, params=params)
        resp.raise_for_status()

        # Step 5
        if not resp.url.startswith(redirect_uri):
            raise OpenEdXOAuth2Error(
                f"Redirected to '{resp.url}', expected: '{redirect_uri}'"
            )
        qs = parse_qs(urlparse(resp.url).query)
        if not qs.get(OPENEDX_OAUTH2_ACCESS_TOKEN_PARAM):
            raise OpenEdXOAuth2Error("Did not receive access_token from Open edX")

        # Step 6
        auth = _create_tokens_and_update_auth(
            auth,
            dict(
                code=qs[OPENEDX_OAUTH2_ACCESS_TOKEN_PARAM],
                grant_type="authorization_code",
                client_id=settings.OPENEDX_API_CLIENT_ID,
                client_secret=settings.OPENEDX_API_CLIENT_SECRET,
                redirect_uri=redirect_uri,
            ),
        )

    return auth


def update_edx_user_email(user):
    """
    Updates the LMS email address for the user with the user's current email address
    utilizing the social auth (oauth) mechanism.

    Args:
        user(user.models.User): the user to update the record for
    """
    with requests.Session() as req_session:
        django_session = auth_api.create_user_session(user)
        session_cookie = requests.cookies.create_cookie(
            name=settings.SESSION_COOKIE_NAME,
            domain=urlparse(settings.SITE_BASE_URL).hostname,
            path=settings.SESSION_COOKIE_PATH,
            value=django_session.session_key,
        )
        req_session.cookies.set_cookie(session_cookie)

        url = edx_url(OPENEDX_SOCIAL_LOGIN_XPRO_PATH)
        resp = req_session.get(url)
        resp.raise_for_status()

        redirect_uri = urljoin(
            settings.SITE_BASE_URL, reverse("openedx-private-oauth-complete")
        )
        url = edx_url(OPENEDX_OAUTH2_AUTHORIZE_PATH)
        params = dict(
            client_id=settings.OPENEDX_API_CLIENT_ID,
            scope=" ".join(OPENEDX_OAUTH2_SCOPES),
            redirect_uri=redirect_uri,
            response_type="code",
        )
        resp = req_session.get(url, params=params)
        resp.raise_for_status()


def _create_tokens_and_update_auth(auth, params):
    """
    Updates an OpenEdxApiAuth given the passed params

    Args:
        auth (courseware.models.OpenEdxApiAuth): the api auth credentials to update with the given params
        params (dict): the params to pass to the access token endpoint

    Returns:
        courseware.models.OpenEdxApiAuth:
            the updated auth records
    """
    resp = requests.post(edx_url(OPENEDX_OAUTH2_ACCESS_TOKEN_PATH), data=params)
    resp.raise_for_status()

    result = resp.json()

    # artificially reduce the expiry window since to cover
    expires_in = (
        result["expires_in"] - OPENEDX_OAUTH2_ACCESS_TOKEN_EXPIRY_MARGIN_SECONDS
    )

    auth.refresh_token = result["refresh_token"]
    auth.access_token = result["access_token"]
    auth.access_token_expires_on = now_in_utc() + timedelta(seconds=expires_in)
    auth.save()
    return auth


def repair_faulty_edx_user(user):
    """
    Loops through all Users that are incorrectly configured in edX and attempts to get
    them in the correct state.

    Args:
        user (User): User to repair
        platform (str): The courseware platform

    Returns:
        (bool, bool): Flags indicating whether a new edX user was created and whether a new
                edX auth token was created.
    """
    created_user, created_auth_token = False, False
    if (
        find_object_with_matching_attr(
            user.courseware_users.all(), "platform", value=PLATFORM_EDX
        )
        is None
    ):
        create_edx_user(user)
        created_user = True
    if not hasattr(user, "openedx_api_auth"):
        create_edx_auth_token(user)
        created_auth_token = True
    return created_user, created_auth_token


def repair_faulty_courseware_users():
    """
    Loops through all Users that are incorrectly configured with the courseware and attempts to get
    them in the correct state.

    Returns:
        list of User: Users that were successfully repaired
    """
    now = now_in_utc()
    repaired_users = []
    for user in User.faulty_courseware_users.filter(
        created_on__lt=now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS)
    ):
        try:
            # edX is our only courseware for the time being. If a different courseware is added, this
            # function will need to be updated.
            created_user, created_auth_token = repair_faulty_edx_user(user)
        except HTTPError as exc:
            log.exception(
                "Failed to repair faulty user %s (%s). %s",
                user.username,
                user.email,
                get_error_response_summary(exc.response),
            )
        except Exception:  # pylint: disable=broad-except
            log.exception(
                "Failed to repair faulty user %s (%s)", user.username, user.email
            )
        else:
            if created_user or created_auth_token:
                repaired_users.append(user)
    return repaired_users


def get_valid_edx_api_auth(user, ttl_in_seconds=OPENEDX_AUTH_DEFAULT_TTL_IN_SECONDS):
    """
    Returns a valid api auth, possibly refreshing the tokens

    Args:
        user (users.models.User): the user to get an auth for
        ttl_in_seconds (int): how long the auth credentials need to remain
                              unexpired without needing a refresh (in seconds)

    Returns:
        auth:
            updated OpenEdxApiAuth
    """
    assert (
        ttl_in_seconds < OPENEDX_AUTH_MAX_TTL_IN_SECONDS
    ), f"ttl_in_seconds must be less than {OPENEDX_AUTH_MAX_TTL_IN_SECONDS}"

    expires_after = now_in_utc() + timedelta(seconds=ttl_in_seconds)
    auth = OpenEdxApiAuth.objects.filter(
        user=user, access_token_expires_on__gt=expires_after
    ).first()
    if not auth:
        # if the auth was no longer valid, try to update it
        with transaction.atomic():
            auth = OpenEdxApiAuth.objects.select_for_update().get(user=user)
            # check again once we have an exclusive lock, something else may have refreshed it for us
            if auth.access_token_expires_on > expires_after:
                return auth
            # it's still invalid, so refresh it now
            return _refresh_edx_api_auth(auth)
    # got a valid auth on first attempt
    return auth


def _refresh_edx_api_auth(auth):
    """
    Updates the api tokens for the given auth

    Args:
        auth (courseware.models.OpenEdxApiAuth): the auth to update

    Returns:
        auth:
            updated OpenEdxApiAuth
    """
    # Note: this is subject to thundering herd problems, we should address this at some point
    return _create_tokens_and_update_auth(
        auth,
        dict(
            refresh_token=auth.refresh_token,
            grant_type="refresh_token",
            client_id=settings.OPENEDX_API_CLIENT_ID,
            client_secret=settings.OPENEDX_API_CLIENT_SECRET,
        ),
    )


def get_edx_api_client(user, ttl_in_seconds=OPENEDX_AUTH_DEFAULT_TTL_IN_SECONDS):
    """
    Gets an edx api client instance for the user

    Args:
        user (users.models.User): A user object
        ttl_in_seconds (int): number of seconds the auth credentials for this client should still be valid

    Returns:
         EdxApi: edx api client instance
    """
    try:
        auth = get_valid_edx_api_auth(user, ttl_in_seconds=ttl_in_seconds)
    except OpenEdxApiAuth.DoesNotExist:
        raise NoEdxApiAuthError(
            "{} does not have an associated OpenEdxApiAuth".format(str(user))
        )
    return EdxApi(
        {"access_token": auth.access_token, "api_key": settings.OPENEDX_API_KEY},
        settings.OPENEDX_API_BASE_URL,
        timeout=settings.EDX_API_CLIENT_TIMEOUT,
    )


def get_edx_api_service_client():
    """
    Gets an edx api client instance for the service worker user

    Returns:
         EdxApi: edx api service worker client instance
    """
    if settings.OPENEDX_SERVICE_WORKER_API_TOKEN is None:
        raise ImproperlyConfigured("OPENEDX_SERVICE_WORKER_API_TOKEN is not set")

    edx_client = EdxApi(
        {
            "access_token": settings.OPENEDX_SERVICE_WORKER_API_TOKEN,
            "api_key": settings.OPENEDX_API_KEY,
        },
        settings.OPENEDX_API_BASE_URL,
        timeout=settings.EDX_API_CLIENT_TIMEOUT,
    )

    return edx_client


def get_edx_api_course_detail_client():
    """
    Gets an edx api client instance for use with the grades api

    Returns:
        CourseDetails: edx api course client instance
    """
    edx_client = get_edx_api_service_client()
    return edx_client.course_detail


def get_edx_api_grades_client():
    """
    Gets an edx api client instance for use with the grades api

    Returns:
        UserCurrentGrades: edx api grades client instance
    """
    edx_client = get_edx_api_service_client()
    return edx_client.current_grades


def get_edx_grades_with_users(course_run, user=None):
    """
    Get all current grades for a course run from OpenEdX along with the enrolled user object

    Args:
        course_run (CourseRun): The course run for which to fetch the grades and users
        user (users.models.User): Limit the grades to this user

    Returns:
        List of (UserCurrentGrade, User) tuples
    """
    grades_client = get_edx_api_grades_client()
    if user:
        edx_grade = grades_client.get_student_current_grade(
            user.username, course_run.courseware_id
        )
        yield edx_grade, user
    else:
        edx_course_grades = grades_client.get_course_current_grades(
            course_run.courseware_id
        )
        all_grades = list(edx_course_grades.all_current_grades)
        for edx_grade in all_grades:
            try:
                user = User.objects.get(username=edx_grade.username)
            except User.DoesNotExist:
                log.warning("User with username %s not found", edx_grade.username)
            else:
                yield edx_grade, user


def enroll_in_edx_course_runs(user, course_runs):
    """
    Enrolls a user in edx course runs

    Args:
        user (users.models.User): The user to enroll
        course_runs (iterable of CourseRun): The course runs to enroll in

    Returns:
        list of edx_api.enrollments.models.Enrollment:
            The results of enrollments via the edx API client

    Raises:
        EdxApiEnrollErrorException: Raised if the underlying edX API HTTP request fails
        UnknownEdxApiEnrollException: Raised if an unknown error was encountered during the edX API request
    """
    edx_client = get_edx_api_client(user)
    results = []
    for course_run in course_runs:
        try:
            result = edx_client.enrollments.create_student_enrollment(
                course_run.courseware_id, mode=EDX_ENROLLMENT_PRO_MODE
            )
            results.append(result)
        except HTTPError as exc:
            # If there is an error message and it indicates that the preferred enrollment mode was the cause of the
            # error, log an error and try to enroll the user in 'audit' mode as a failover.
            if not is_json_response(exc.response):
                raise EdxApiEnrollErrorException(user, course_run, exc) from exc
            error_msg = exc.response.json().get("message", "")
            is_enroll_mode_error = any(
                [error_text in error_msg for error_text in PRO_ENROLL_MODE_ERROR_TEXTS]
            )
            if not is_enroll_mode_error:
                raise EdxApiEnrollErrorException(user, course_run, exc) from exc
            log.error(
                "Failed to enroll user in %s with '%s' mode. Attempting to enroll with '%s' mode instead. "
                "(%s)",
                course_run.courseware_id,
                EDX_ENROLLMENT_PRO_MODE,
                EDX_ENROLLMENT_AUDIT_MODE,
                get_error_response_summary(exc.response),
            )
            try:
                result = edx_client.enrollments.create_student_enrollment(
                    course_run.courseware_id, mode=EDX_ENROLLMENT_AUDIT_MODE
                )
            except HTTPError as inner_exc:
                raise EdxApiEnrollErrorException(
                    user, course_run, inner_exc
                ) from inner_exc
            except Exception as inner_exc:  # pylint: disable=broad-except
                raise UnknownEdxApiEnrollException(
                    user, course_run, inner_exc
                ) from inner_exc
            results.append(result)
        except Exception as exc:  # pylint: disable=broad-except
            raise UnknownEdxApiEnrollException(user, course_run, exc) from exc
    return results


def retry_failed_edx_enrollments():
    """
    Gathers all CourseRunEnrollments with edx_enrolled=False and retries them via the edX API

    Returns:
        list of CourseRunEnrollment: All CourseRunEnrollments that were successfully retried
    """
    now = now_in_utc()
    failed_run_enrollments = CourseRunEnrollment.objects.select_related(
        "user", "run"
    ).filter(
        user__is_active=True,
        edx_enrolled=False,
        created_on__lt=now - timedelta(minutes=COURSEWARE_REPAIR_GRACE_PERIOD_MINS),
    )
    succeeded = []
    for enrollment in failed_run_enrollments:
        user = enrollment.user
        course_run = enrollment.run
        try:
            enroll_in_edx_course_runs(user, [course_run])
        except Exception as exc:  # pylint: disable=broad-except
            log.exception(str(exc))
        else:
            enrollment.edx_enrolled = True
            enrollment.save_and_log(None)
            succeeded.append(enrollment)
    return succeeded


def unenroll_edx_course_run(run_enrollment):
    """
    Unenrolls/deactivates a user in an edx course run

    Args:
        run_enrollment (CourseRunEnrollment): The enrollment record that represents the
            currently-enrolled course run

    Returns:
        edx_api.enrollments.models.Enrollment:
            The resulting Enrollment object (which should be set to inactive)

    Raises:
        EdxApiEnrollErrorException: Raised if the underlying edX API HTTP request fails
        UnknownEdxApiEnrollException: Raised if an unknown error was encountered during the edX API request
    """
    edx_client = get_edx_api_client(run_enrollment.user)
    try:
        deactivated_enrollment = edx_client.enrollments.deactivate_enrollment(
            run_enrollment.run.courseware_id
        )
    except HTTPError as exc:
        raise EdxApiEnrollErrorException(run_enrollment.user, run_enrollment.run, exc)
    except Exception as exc:  # pylint: disable=broad-except
        raise UnknownEdxApiEnrollException(run_enrollment.user, run_enrollment.run, exc)
    else:
        return deactivated_enrollment


def update_edx_user_name(user):
    """
    Makes a request to update user's name on edx if changed in xPRO

    Args:
        user (user.models.User): the application user

    Returns:
        edx_api.user_info.models.Info: Object representing updated details of user in edX

    Raises:
        UserNameUpdateFailedException: Raised if underlying edX API request fails due to any reason
    """

    edx_client = get_edx_api_client(user)
    try:
        return edx_client.user_info.update_user_name(user.username, user.name)
    except Exception as exc:
        raise UserNameUpdateFailedException(
            "Error updating user's full name in edX.", exc
        )
