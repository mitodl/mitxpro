"""User app utility functions"""

import logging
from email.utils import formataddr

from django.contrib.auth import get_user_model
from requests.exceptions import HTTPError

from mitxpro.utils import get_error_response_summary

User = get_user_model()
log = logging.getLogger(__name__)


def ensure_active_user(user):
    """
    Activates the user (if required) and generates Open edX credentials and corresponding user if
    necessary

    Args:
        user (users.models.User): The user to activate/verify as functional
    """
    from courseware.api import repair_faulty_edx_user  # circular import issues

    if not user.is_active:
        user.is_active = True
        user.save()
        log.info("User %s activated", user.email)

    # Check if the user is properly onboard with edX (has proper auth credentials)
    # and try to repair if necessary
    if User.faulty_courseware_users.filter(pk=user.id).exists():
        try:
            created_user, created_auth_token = repair_faulty_edx_user(user)
            if created_user:
                log.info("Created edX user for %s", user.email)
            if created_auth_token:
                log.info("Created edX auth token for %s", user.email)
        except HTTPError as exc:
            log.error(  # noqa: TRY400
                "%s (%s): Failed to repair (%s)",
                user.username,
                user.email,
                get_error_response_summary(exc.response),
            )
        except Exception:
            log.exception("%s (%s): Failed to repair", user.username, user.email)


def format_recipient(user: User) -> str:
    """Format the user as a recipient"""
    return formataddr((user.name, user.email))
