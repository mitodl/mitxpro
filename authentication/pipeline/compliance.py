"""Compliance pipeline actions"""
import logging

from django.conf import settings
from django.core import mail
from social_core.exceptions import AuthException

from authentication.exceptions import (
    UserExportBlockedException,
    UserTryAgainLaterException,
)
from compliance import api


log = logging.getLogger()


def verify_exports_compliance(
    strategy, backend, user=None, **kwargs
):  # pylint: disable=unused-argument
    """
    Verify that the user is allowed by exports compliance

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        user (User): the current user
    """
    if not api.is_exports_verification_enabled():
        log.warning("Export compliance checks are disabled")
        return {}

    # skip this step if the user is active or they have an existing export inquiry logged
    if user.is_active and user.exports_inquiries.exists():
        return {}

    try:
        export_inquiry = api.verify_user_with_exports(user)
    except Exception as exc:  # pylint: disable=broad-except
        # hard failure to request the exports API, log an error but don't let the user proceed
        log.exception("Unable to verify exports compliance")
        raise UserTryAgainLaterException(backend) from exc

    if export_inquiry is None:
        raise UserTryAgainLaterException(backend)
    elif export_inquiry.is_denied:
        log.info(
            "User with email '%s' was denied due to exports violation, for reason_code=%s, info_code=%s",
            user.email,
            export_inquiry.reason_code,
            export_inquiry.info_code,
        )
        try:
            with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
                mail.send_mail(
                    f"Exports Compliance: denied {user.email}",
                    f"User with email '{user.email}' was denied due to exports violation, for reason_code={export_inquiry.reason_code}, info_code={export_inquiry.info_code}",
                    settings.MAILGUN_FROM_EMAIL,
                    [settings.EMAIL_SUPPORT],
                    connection=connection,
                )
        except Exception:  # pylint: disable=broad-except
            log.exception(
                "Exception sending email to support regarding export compliance check failure"
            )
        raise UserExportBlockedException(backend)
    elif export_inquiry.is_unknown:
        raise AuthException("Unable to authenticate, please contact support")

    return {}
