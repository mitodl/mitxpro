"""Auth pipline functions for user authentication"""

import json
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from mitol.common.utils import dict_without_keys
from social_core.backends.email import EmailAuth
from social_core.exceptions import AuthAlreadyAssociated, AuthException
from social_core.pipeline.partial import partial

from affiliate.api import get_affiliate_id_from_request
from authentication.exceptions import (
    EmailBlockedException,
    InvalidPasswordException,
    RequirePasswordAndPersonalInfoException,
    RequirePasswordException,
    RequireProfileException,
    RequireRegistrationException,
    UnexpectedExistingUserException,
    UserCreationFailedException,
)
from authentication.utils import SocialAuthState, is_user_email_blocked
from compliance import api as compliance_api
from courseware import api as courseware_api
from courseware import tasks as courseware_tasks
from hubspot_xpro.task_helpers import sync_hubspot_user
from users.serializers import ProfileSerializer, UserSerializer
from mitol.common.utils.user import usernameify, create_user_with_generated_username

log = logging.getLogger()

User = get_user_model()

CREATE_COURSEWARE_USER_RETRY_DELAY = 60
NAME_MIN_LENGTH = 2


def validate_email_auth_request(
    strategy,  # noqa: ARG001
    backend,
    user=None,
    *args,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
):
    """
    Validates an auth request for email

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
    """
    if backend.name != EmailAuth.name:
        return {}

    # if there's a user, force this to be a login
    if user is not None:
        return {"flow": SocialAuthState.FLOW_LOGIN}

    return {}


def get_username(
    strategy,
    backend,  # noqa: ARG001
    user=None,
    *args,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
):
    """
    Gets the username for a user

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
    """
    return {"username": None if not user else strategy.storage.user.get_username(user)}


@partial
def create_user_via_email(
    strategy,
    backend,
    user=None,
    flow=None,
    current_partial=None,
    *args,  # noqa: ARG001
    **kwargs,
):
    """
    Creates a new user if needed and sets the password and name.
    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
        details (dict): Dict of user details
        flow (str): the type of flow (login or register)
        current_partial (Partial): the partial for the step in the pipeline

    Raises:
        RequirePasswordAndPersonalInfoException: if the user hasn't set password or name
    """
    if backend.name != EmailAuth.name or flow != SocialAuthState.FLOW_REGISTER:
        return {}

    if user is not None:
        raise UnexpectedExistingUserException(backend, current_partial)

    context = {}
    data = strategy.request_data().copy()
    if "name" not in data or "password" not in data:
        raise RequirePasswordAndPersonalInfoException(backend, current_partial)
    if len(data.get("name", 0)) < NAME_MIN_LENGTH:
        raise RequirePasswordAndPersonalInfoException(
            backend,
            current_partial,
            errors=["Full name must be at least 2 characters long."],
        )

    data["email"] = kwargs.get("email", kwargs.get("details", {}).get("email"))

    if User.objects.filter(email__iexact=data["email"]).exists():
        raise AuthAlreadyAssociated(backend)

    username = usernameify(data["name"], email=data["email"])
    data["username"] = username

    affiliate_id = get_affiliate_id_from_request(strategy.request)
    if affiliate_id is not None:
        context["affiliate_id"] = affiliate_id

    serializer = UserSerializer(data=data, context=context)

    if not serializer.is_valid():
        raise RequirePasswordAndPersonalInfoException(
            backend,
            current_partial,
            errors=serializer.errors.get("non_field_errors"),
            field_errors=dict_without_keys(serializer.errors, "non_field_errors"),
        )

    try:
        created_user = create_user_with_generated_username(
            serializer, username, username_field="username", max_length=30
        )
        if created_user is None:
            raise IntegrityError(  # noqa: TRY301
                f"Failed to create User with generated username ({username})"  # noqa: EM102
            )
    except Exception as exc:
        raise UserCreationFailedException(backend, current_partial) from exc

    return {"is_new": True, "user": created_user, "username": created_user.username}


@partial
def create_profile(
    strategy,
    backend,
    user=None,
    flow=None,  # noqa: ARG001
    current_partial=None,
    *args,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
):
    """
    Creates a new profile for the user
    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
        flow (str): the type of flow (login or register)
        current_partial (Partial): the partial for the step in the pipeline

    Raises:
        RequireProfileException: if the profile data is missing or invalid
    """
    if backend.name != EmailAuth.name or user.profile.is_complete:
        return {}

    data = strategy.request_data().copy()

    serializer = ProfileSerializer(instance=user.profile, data=data)
    if not serializer.is_valid():
        raise RequireProfileException(
            backend, current_partial, errors=serializer.errors
        )
    serializer.save()
    sync_hubspot_user(user)
    return {}


@partial
def validate_email(
    strategy,
    backend,
    user=None,  # noqa: ARG001
    flow=None,  # noqa: ARG001
    current_partial=None,
    *args,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
):
    """
    Validates a user's email for register

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
        flow (str): the type of flow (login or register)
        current_partial (Partial): the partial for the step in the pipeline

    Raises:
        EmailBlockedException: if the user email is blocked
    """
    data = strategy.request_data()
    authentication_flow = data.get("flow")
    if authentication_flow == SocialAuthState.FLOW_REGISTER and "email" in data:  # noqa: SIM102
        if is_user_email_blocked(data["email"]):
            raise EmailBlockedException(backend, current_partial)
    return {}


@partial
def validate_password(
    strategy,
    backend,
    user=None,
    flow=None,
    current_partial=None,
    *args,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
):
    """
    Validates a user's password for login

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
        flow (str): the type of flow (login or register)
        current_partial (Partial): the partial for the step in the pipeline

    Raises:
        RequirePasswordException: if the user password is invalid
    """
    if backend.name != EmailAuth.name or flow != SocialAuthState.FLOW_LOGIN:
        return {}

    data = strategy.request_data()
    if user is None:
        raise RequireRegistrationException(backend, current_partial)

    if "password" not in data:
        raise RequirePasswordException(backend, current_partial)

    password = data["password"]

    if not user or not user.check_password(password):
        raise InvalidPasswordException(backend, current_partial)

    return {}


def forbid_hijack(strategy, backend, **kwargs):  # noqa: ARG001
    """
    Forbid an admin user from trying to login/register while hijacking another user

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
    """
    # As first step in pipeline, stop a hijacking admin from going any further
    if bool(strategy.session_get("hijack_history")):
        raise AuthException("You are hijacking another user, don't try to login again")  # noqa: EM101
    return {}


def activate_user(
    strategy,  # noqa: ARG001
    backend,  # noqa: ARG001
    user=None,
    is_new=False,  # noqa: ARG001, FBT002
    **kwargs,  # noqa: ARG001
):
    """
    Activate the user's account if they passed export controls

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
    """
    if user.is_active:
        return {}

    export_inquiry = compliance_api.get_latest_exports_inquiry(user)

    # if the user has an export inquiry that is considered successful, activate them
    if not compliance_api.is_exports_verification_enabled() or (
        export_inquiry is not None and export_inquiry.is_success
    ):
        user.is_active = True
        user.save()

    return {}


def create_courseware_user(
    strategy,  # noqa: ARG001
    backend,  # noqa: ARG001
    user=None,
    is_new=False,  # noqa: FBT002
    **kwargs,  # noqa: ARG001
):
    """
    Create a user in the courseware, deferring a retry via celery if it fails

    Args:
        user (users.models.User): the user that was just created
        is_new (bool): True if the user was just created
    """
    if not is_new or not user.is_active:
        return {}

    try:
        courseware_api.create_user(user)
    except Exception:
        log.exception("Error creating courseware user records on User create")
        # try again later
        courseware_tasks.create_user_from_id.apply_async(
            (user.id,), countdown=CREATE_COURSEWARE_USER_RETRY_DELAY
        )

    return {}


def send_user_to_hubspot(request, **kwargs):
    """
    Create a hubspot contact using the hubspot Forms API
    Submit the user's email and optionally a hubspotutk cookie
    """
    portal_id = settings.HUBSPOT_CONFIG.get("HUBSPOT_PORTAL_ID")
    form_id = settings.HUBSPOT_CONFIG.get("HUBSPOT_CREATE_USER_FORM_ID")

    if not (portal_id and form_id):
        return {}

    hutk = request.COOKIES.get("hubspotutk")
    email = kwargs.get("email", kwargs.get("details", {}).get("email"))

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    data = {"email": email}

    if hutk:
        data["hs_context"] = json.dumps({"hutk": hutk})

    url = f"https://forms.hubspot.com/uploads/form/v2/{portal_id}/{form_id}?&"

    requests.post(url=url, data=data, headers=headers)  # noqa: S113

    return {}


def sync_user_to_hubspot(
    strategy,  # noqa: ARG001
    backend,  # noqa: ARG001
    user=None,
    is_new=False,  # noqa: ARG001, FBT002
    **kwargs,  # noqa: ARG001
):
    """
    Sync the user's latest profile data with hubspot on login
    """
    if user.is_active:
        sync_hubspot_user(user)
    return {}
