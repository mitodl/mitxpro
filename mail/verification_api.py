"""API for email verifications"""
from urllib.parse import quote_plus

from django.urls import reverse

from affiliate.api import get_affiliate_code_from_request
from affiliate.constants import AFFILIATE_QS_PARAM
from mail import api
from mail.constants import EMAIL_VERIFICATION, EMAIL_CHANGE_EMAIL


def send_verification_email(
    strategy, backend, code, partial_token
):  # pylint: disable=unused-argument
    """
    Sends a verification email for python-social-auth

    Args:
        strategy (social_django.strategy.DjangoStrategy): the strategy used to authenticate
        backend (social_core.backends.base.BaseAuth): the backend being used to authenticate
        code (social_django.models.Code): the confirmation code used to confirm the email address
        partial_token (str): token used to resume a halted pipeline
    """
    url = "{}?verification_code={}&partial_token={}".format(
        strategy.build_absolute_uri(reverse("register-confirm")),
        quote_plus(code.code),
        quote_plus(partial_token),
    )

    affiliate_code = get_affiliate_code_from_request(strategy.request)
    if affiliate_code is not None:
        url = f"{url}&{AFFILIATE_QS_PARAM}={affiliate_code}"

    api.send_message(
        api.message_for_recipient(
            code.email,
            api.context_for_user(extra_context={"confirmation_url": url}),
            EMAIL_VERIFICATION,
        )
    )


def send_verify_email_change_email(request, change_request):
    """
    Sends a verification email for a user email change
    Args:
        request (django.http.Request): the http request we're sending this email for
        change_request (ChangeEmailRequest): the change request to send the confirmation for
    """

    url = "{}?verification_code={}".format(
        request.build_absolute_uri(reverse("account-confirm-email-change")),
        quote_plus(change_request.code),
    )

    api.send_messages(
        list(
            api.messages_for_recipients(
                [
                    (
                        change_request.new_email,
                        api.context_for_user(extra_context={"confirmation_url": url}),
                    )
                ],
                EMAIL_CHANGE_EMAIL,
            )
        )
    )
