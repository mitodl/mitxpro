"""Auth pipline functions for user authentication"""
import logging

from social_core.backends.email import EmailAuth
from social_core.exceptions import AuthException
from social_core.pipeline.partial import partial
from django.db import IntegrityError

from authentication.exceptions import (
    InvalidPasswordException,
    RequirePasswordException,
    RequirePasswordAndPersonalInfoException,
    RequireProfileException,
    RequireRegistrationException,
    UnexpectedExistingUserException,
    UserCreationFailedException,
)
from authentication.utils import SocialAuthState
from authentication.api import create_user_with_generated_username

from compliance import api as compliance_api
from courseware import api as courseware_api, tasks as courseware_tasks
from hubspot.task_helpers import sync_hubspot_user
from users.serializers import UserSerializer, ProfileSerializer
from users.utils import usernameify

log = logging.getLogger()

CREATE_COURSEWARE_USER_RETRY_DELAY = 60
NAME_MIN_LENGTH = 2

# pylint: disable=keyword-arg-before-vararg


def validate_email_auth_request(
    strategy, backend, user=None, *args, **kwargs
):  # pylint: disable=unused-argument
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
    strategy, backend, user=None, *args, **kwargs
):  # pylint: disable=unused-argument
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
    strategy, backend, user=None, flow=None, current_partial=None, *args, **kwargs
):  # pylint: disable=too-many-arguments,unused-argument
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
    username = usernameify(data["name"], email=data["email"])
    data["username"] = username
    serializer = UserSerializer(data=data)

    if not serializer.is_valid():
        raise RequirePasswordAndPersonalInfoException(
            backend, current_partial, errors=serializer.errors
        )

    try:
        created_user = create_user_with_generated_username(serializer, username)
        if created_user is None:
            raise IntegrityError(
                "Failed to create User with generated username ({})".format(username)
            )
    except Exception as exc:
        raise UserCreationFailedException(backend, current_partial) from exc

    return {"is_new": True, "user": created_user, "username": created_user.username}


@partial
def create_profile(
    strategy, backend, user=None, flow=None, current_partial=None, *args, **kwargs
):  # pylint: disable=too-many-arguments,unused-argument
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
def validate_password(
    strategy, backend, user=None, flow=None, current_partial=None, *args, **kwargs
):  # pylint: disable=unused-argument
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


def forbid_hijack(strategy, backend, **kwargs):  # pylint: disable=unused-argument
    """
    Forbid an admin user from trying to login/register while hijacking another user

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
    """
    # As first step in pipeline, stop a hijacking admin from going any further
    if strategy.session_get("is_hijacked_user"):
        raise AuthException("You are hijacking another user, don't try to login again")
    return {}


def activate_user(
    strategy, backend, user=None, is_new=False, **kwargs
):  # pylint: disable=unused-argument
    """
    Activate the user's account if they passed export controls

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
    """
    if user.is_active or not is_new:
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
    strategy, backend, user=None, is_new=False, **kwargs
):  # pylint: disable=unused-argument
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
    except Exception:  # pylint: disable=broad-except
        log.exception("Error creating courseware user records on User create")
        # try again later
        courseware_tasks.create_user_from_id.apply_async(
            (user.id,), countdown=CREATE_COURSEWARE_USER_RETRY_DELAY
        )

    return {}
