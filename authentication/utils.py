"""Authentication utils"""

import hashlib

from social_core.utils import get_strategy
from social_django.utils import STORAGE

from users.models import BlockList


class SocialAuthState:
    """Social auth state"""

    FLOW_REGISTER = "register"
    FLOW_LOGIN = "login"

    # login states
    STATE_LOGIN_EMAIL = "login/email"
    STATE_LOGIN_PASSWORD = "login/password"  # noqa: S105
    STATE_LOGIN_PROVIDER = "login/provider"

    # registration states
    STATE_REGISTER_EMAIL = "register/email"
    STATE_REGISTER_CONFIRM_SENT = "register/confirm-sent"
    STATE_REGISTER_CONFIRM = "register/confirm"
    STATE_REGISTER_DETAILS = "register/details"
    STATE_REGISTER_EXTRA_DETAILS = "register/extra"
    STATE_REGISTER_REQUIRED = "register/required"

    # end states
    STATE_SUCCESS = "success"
    STATE_ERROR = "error"
    STATE_ERROR_TEMPORARY = "error-temporary"
    STATE_INACTIVE = "inactive"
    STATE_INVALID_EMAIL = "invalid-email"
    STATE_USER_BLOCKED = "user-blocked"
    STATE_INVALID_LINK = "invalid-link"
    STATE_EXISTING_ACCOUNT = "existing-account"

    def __init__(  # noqa: PLR0913
        self,
        state,
        *,
        provider=None,
        partial=None,
        flow=None,
        errors=None,
        field_errors=None,
        redirect_url=None,
        user=None,
    ):
        self.state = state
        self.partial = partial
        self.flow = flow
        self.provider = provider
        self.errors = errors or []
        self.field_errors = field_errors or {}
        self.redirect_url = redirect_url
        self.user = user

    def get_partial_token(self):
        """Return the partial token or None"""
        return self.partial.token if self.partial else None


def load_drf_strategy(request=None):
    """Returns the DRF strategy"""
    return get_strategy(
        "authentication.strategy.DjangoRestFrameworkStrategy", STORAGE, request
    )


def get_md5_hash(value):
    """Returns the md5 hash object for the given value"""
    return hashlib.md5(value.lower().encode("utf-8"))  # noqa: S324


def is_user_email_blocked(email):
    """Returns the user's email blocked status"""
    hash_object = get_md5_hash(email)
    return BlockList.objects.filter(hashed_email=hash_object.hexdigest()).exists()


def block_user_email(email):
    """Blocks the user's email if provided"""
    msg = None
    if email:
        hash_object = get_md5_hash(email)
        _, created = BlockList.objects.get_or_create(
            hashed_email=hash_object.hexdigest()
        )
        if created:
            msg = f"Email {email} is added to the blocklist of MIT xPRO."
        else:
            msg = f"Email {email} is already marked blocked for MIT xPRO."
    return msg
