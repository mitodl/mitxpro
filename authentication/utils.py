"""Authentication utils"""
from social_core.utils import get_strategy
from social_django.utils import STORAGE


class SocialAuthState:  # pylint: disable=too-many-instance-attributes
    """Social auth state"""

    FLOW_REGISTER = "register"
    FLOW_LOGIN = "login"

    # login states
    STATE_LOGIN_EMAIL = "login/email"
    STATE_LOGIN_PASSWORD = "login/password"
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

    def __init__(
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
    ):  # pylint: disable=too-many-arguments
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
