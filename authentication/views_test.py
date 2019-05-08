"""Tests for authentication views"""
# pylint: disable=redefined-outer-name

from django.contrib.auth import get_user, get_user_model
from django.urls import reverse
import factory
import pytest
from rest_framework import status
from social_core.backends.email import EmailAuth

from authentication.serializers import PARTIAL_PIPELINE_TOKEN_KEY
from authentication.utils import SocialAuthState
from users.factories import UserSocialAuthFactory
from mitxpro.test_utils import any_instance_of, MockResponse

pytestmark = [pytest.mark.django_db]

NEW_EMAIL = "test@example.com"
NEXT_URL = "/next/url"

User = get_user_model()


@pytest.fixture
def email_user(user):
    """Fixture for a user that has an 'email' type UserSocialAuth"""
    UserSocialAuthFactory.create(user=user, provider=EmailAuth.name, uid=user.email)
    return user


# pylint:disable=too-many-arguments
def assert_api_call(
    client,
    url,
    payload,
    expected,
    expect_authenticated=False,
    expect_status=status.HTTP_200_OK,
    use_defaults=True,
):
    """Run the API call and perform basic assertions"""
    assert bool(get_user(client).is_authenticated) is False

    response = client.post(reverse(url), payload, content_type="application/json")
    actual = response.json()

    defaults = {
        "errors": [],
        "redirect_url": None,
        "extra_data": {},
        "state": None,
        "provider": None,
        "flow": None,
        "partial_token": any_instance_of(str),
    }

    assert actual == ({**defaults, **expected} if use_defaults else expected)
    assert response.status_code == expect_status

    assert bool(get_user(client).is_authenticated) is expect_authenticated

    return actual


@pytest.fixture()
def mock_email_send(mocker):
    """Mock the email send API"""
    yield mocker.patch("mail.verification_api.send_verification_email")


@pytest.fixture()
def mock_recaptcha_success(mocker):
    """ Mock Google recaptcha request"""
    yield mocker.patch(
        "authentication.views.requests.post",
        return_value=MockResponse(
            content='{"success": true}', status_code=status.HTTP_200_OK
        ),
    )


@pytest.fixture()
def mock_recaptcha_failure(mocker):
    """ Mock Google recaptcha request"""
    yield mocker.patch(
        "authentication.views.requests.post",
        return_value=MockResponse(
            content='{"success": false, "error-codes": ["bad-request"]}',
            status_code=status.HTTP_200_OK,
        ),
    )


@pytest.fixture()
def login_email_exists(client, email_user):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        return assert_api_call(
            client,
            "psa-login-email",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "email": email_user.email,
                "next": NEXT_URL,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "state": SocialAuthState.STATE_LOGIN_PASSWORD,
                "extra_data": {"name": email_user.name},
            },
        )

    yield run_step


@pytest.fixture()
def login_email_next(client, email_user):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        return assert_api_call(
            client,
            "psa-login-email",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "email": email_user.email,
                "next": NEXT_URL,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "state": SocialAuthState.STATE_LOGIN_PASSWORD,
                "extra_data": {"name": email_user.name},
            },
        )

    yield run_step


@pytest.fixture()
def register_email_exists(client, user, mock_email_send):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        result = assert_api_call(
            client,
            "psa-register-email",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "email": user.email,
                "next": NEXT_URL,
            },
            {
                "errors": ["Password is required to login"],
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "state": SocialAuthState.STATE_LOGIN_PASSWORD,
            },
        )
        mock_email_send.assert_not_called()
        return result

    yield run_step


@pytest.fixture()
def login_email_not_exists(client):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        result = assert_api_call(
            client,
            "psa-login-email",
            {"flow": SocialAuthState.FLOW_LOGIN, "email": NEW_EMAIL},
            {
                "errors": ["Couldn't find your account"],
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "partial_token": None,
                "state": SocialAuthState.STATE_ERROR,
            },
        )
        assert User.objects.filter(email=NEW_EMAIL).exists() is False
        return result

    yield run_step


@pytest.fixture()
def register_email_not_exists(client, mock_email_send):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        result = assert_api_call(
            client,
            "psa-register-email",
            {"flow": SocialAuthState.FLOW_REGISTER, "email": NEW_EMAIL},
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "partial_token": None,
                "state": SocialAuthState.STATE_REGISTER_CONFIRM_SENT,
            },
        )
        mock_email_send.assert_called_once()
        assert User.objects.filter(email=NEW_EMAIL).exists() is False
        return result

    yield run_step


@pytest.fixture()
def register_email_not_exists_with_recaptcha(
    settings, client, mock_email_send, mock_recaptcha_success
):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        settings.RECAPTCHA_SITE_KEY = "fake"
        result = assert_api_call(
            client,
            "psa-register-email",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "email": NEW_EMAIL,
                "recaptcha": "fake",
            },
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "partial_token": None,
                "state": SocialAuthState.STATE_REGISTER_CONFIRM_SENT,
            },
        )
        mock_recaptcha_success.assert_called_once()
        mock_email_send.assert_called_once()
        return result

    yield run_step


@pytest.fixture()
def register_email_not_exists_with_recaptcha_invalid(
    settings, client, mock_email_send, mock_recaptcha_failure
):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        settings.RECAPTCHA_SITE_KEY = "fake"
        result = assert_api_call(
            client,
            "psa-register-email",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "email": NEW_EMAIL,
                "recaptcha": "fake",
            },
            {"error-codes": ["bad-request"], "success": False},
            expect_status=status.HTTP_400_BAD_REQUEST,
            use_defaults=False,
        )
        mock_recaptcha_failure.assert_called_once()
        mock_email_send.assert_not_called()
        return result

    yield run_step


@pytest.fixture()
def login_password_valid(client, user):
    """Yield a function for this step"""
    password = "password1"

    def run_step(last_result):
        """Run the step"""
        user.set_password(password)
        user.save()
        return assert_api_call(
            client,
            "psa-login-password",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "partial_token": last_result["partial_token"],
                "password": password,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "redirect_url": NEXT_URL,
                "partial_token": None,
                "state": SocialAuthState.STATE_SUCCESS,
            },
            expect_authenticated=True,
        )

    yield run_step


@pytest.fixture()
def login_password_user_inactive(client, user):
    """Yield a function for this step"""
    password = "password1"

    def run_step(last_result):
        """Run the step"""
        user.is_active = False
        user.set_password(password)
        user.save()
        return assert_api_call(
            client,
            "psa-login-password",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "partial_token": last_result["partial_token"],
                "password": password,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "partial_token": None,
                "state": SocialAuthState.STATE_INACTIVE,
            },
        )

    yield run_step


@pytest.fixture()
def login_password_invalid(client, user):
    """Yield a function for this step"""

    def run_step(last_result):
        """Run the step"""
        user.set_password("password1")
        user.save()
        return assert_api_call(
            client,
            "psa-login-password",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "partial_token": last_result["partial_token"],
                "password": "invalidpass",
            },
            {
                "errors": ["Unable to login with that email and password combination"],
                "flow": SocialAuthState.FLOW_LOGIN,
                "provider": EmailAuth.name,
                "state": SocialAuthState.STATE_ERROR,
            },
        )

    yield run_step


@pytest.fixture()
def redeem_confirmation_code(client, mock_email_send):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        _, _, code, partial_token = mock_email_send.call_args[0]
        return assert_api_call(
            client,
            "psa-register-confirm",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "verification_code": code.code,
                "partial_token": partial_token,
            },
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "state": SocialAuthState.STATE_REGISTER_DETAILS,
            },
        )

    yield run_step


@pytest.fixture()
def redeem_confirmation_code_twice(client, mock_email_send):
    """Yield a function for this step"""

    def run_step(last_result):  # pylint: disable=unused-argument
        """Run the step"""
        _, _, code, partial_token = mock_email_send.call_args[0]
        return assert_api_call(
            client,
            "psa-register-confirm",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "verification_code": code.code,
                "partial_token": partial_token,
            },
            {
                "errors": [],
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "redirect_url": None,
                "partial_token": None,
                "state": SocialAuthState.STATE_INVALID_EMAIL,
            },
        )

    yield run_step


@pytest.fixture()
def register_user_details(client):
    """Yield a function for this step"""

    def run_step(last_result):
        """Run the step"""
        return assert_api_call(
            client,
            "psa-register-details",
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "partial_token": last_result["partial_token"],
                "password": "password1",
                "name": "Sally Smith",
                "legal_address": {
                    "first_name": "Sally",
                    "last_name": "Smith",
                    "street_address": ["Main Street"],
                    "country": "US",
                    "state_or_territory": "US-CO",
                    "city": "Boulder",
                    "postal_code": "02183",
                },
            },
            {
                "flow": SocialAuthState.FLOW_REGISTER,
                "provider": EmailAuth.name,
                "partial_token": None,
                "state": SocialAuthState.STATE_SUCCESS,
            },
            expect_authenticated=True,
        )

    yield run_step


@pytest.mark.betamax
@pytest.mark.usefixture("mock_email_send")
@pytest.mark.parametrize(
    "steps",
    [
        ["login_email_exists", "login_password_valid"],
        ["login_email_exists", "login_password_invalid"],
        ["login_email_exists", "login_password_user_inactive"],
        ["login_email_not_exists"],
        ["register_email_exists", "login_password_valid"],
        ["register_email_exists", "login_password_invalid"],
        [
            "register_email_not_exists",
            "redeem_confirmation_code",
            "register_user_details",
        ],
        [
            "register_email_not_exists_with_recaptcha",
            "redeem_confirmation_code",
            "register_user_details",
        ],
        [
            "register_email_not_exists",
            "redeem_confirmation_code",
            "redeem_confirmation_code_twice",
        ],
        ["register_email_not_exists_with_recaptcha_invalid"],
    ],
    ids=lambda arg: "->".join(arg) if isinstance(arg, list) else None,
)
def test_login_register_flows(request, steps):
    """Walk the steps and assert expected results"""
    last_result = None
    for fixture_name in steps:
        assert_step = request.getfixturevalue(fixture_name)
        last_result = assert_step(last_result)


def test_new_register_no_session_partial(client):
    """
    When a user registers for the first time and a verification email is sent, the partial
    token should be cleared from the session. The Partial object associated with that token should
    only be used when it's matched from the email verification link.
    """
    assert_api_call(
        client,
        "psa-register-email",
        {"flow": SocialAuthState.FLOW_REGISTER, "email": NEW_EMAIL},
        {
            "flow": SocialAuthState.FLOW_REGISTER,
            "provider": EmailAuth.name,
            "partial_token": None,
            "state": SocialAuthState.STATE_REGISTER_CONFIRM_SENT,
        },
    )
    assert PARTIAL_PIPELINE_TOKEN_KEY not in client.session.keys()


def test_login_email_error(client, mocker):
    """Tests email login with error result"""
    assert bool(get_user(client).is_authenticated) is False

    mocked_authenticate = mocker.patch(
        "authentication.serializers.SocialAuthSerializer._authenticate"
    )
    mocked_authenticate.return_value = "invalid"

    # start login with email
    response = client.post(
        reverse("psa-login-email"),
        {"flow": SocialAuthState.FLOW_LOGIN, "email": "anything@example.com"},
    )
    assert response.json() == {
        "errors": [],
        "flow": SocialAuthState.FLOW_LOGIN,
        "provider": EmailAuth.name,
        "redirect_url": None,
        "partial_token": None,
        "state": SocialAuthState.STATE_ERROR,
        "extra_data": {},
    }
    assert response.status_code == status.HTTP_200_OK

    assert bool(get_user(client).is_authenticated) is False


def test_login_email_hijacked(client, user, admin_user):
    """ Test that a 403 response is returned for email login view if user is hijacked"""
    client.force_login(admin_user)
    client.post("/hijack/{}/".format(user.id))
    response = client.post(
        reverse("psa-login-email"),
        {"flow": SocialAuthState.FLOW_LOGIN, "email": "anything@example.com"},
    )
    assert response.status_code == 403


def test_register_email_hijacked(client, user, admin_user):
    """ Test that a 403 response is returned for email register view if user is hijacked"""
    client.force_login(admin_user)
    client.post("/hijack/{}/".format(user.id))
    response = client.post(
        reverse("psa-register-email"),
        {"flow": SocialAuthState.FLOW_LOGIN, "email": "anything@example.com"},
    )
    assert response.status_code == 403


class DjoserViewTests:
    """Tests for views that modify Djoser views"""

    # pylint: disable=too-many-arguments
    @pytest.mark.parametrize(
        "url", ["password-reset-api", "password-reset-confirm-api", "set-password-api"]
    )
    def test_password_reset_coerce_204(self, mocker, client, user, url):
        """
        Verify that password reset views coerce a 204 response to a 200 in order
        to play nice with redux-hammock.
        """
        mocker.patch(
            "authentication.views.ActionViewMixin.post",
            return_value=mocker.Mock(status_code=status.HTTP_400_BAD_REQUEST),
        )
        client.force_login(user)
        response = client.post(reverse(url), {})
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {}

    @pytest.mark.parametrize(
        "response_status,expected_session_update",
        [
            [status.HTTP_200_OK, True],
            [status.HTTP_204_NO_CONTENT, True],
            [status.HTTP_400_BAD_REQUEST, False],
        ],
    )
    def test_password_change_session_update(
        self, mocker, response_status, expected_session_update, client, user
    ):
        """
        Tests that the password change view updates the Django session when the
        request succeeds.
        """
        mocker.patch(
            "authentication.views.ActionViewMixin.post",
            return_value=mocker.Mock(status_code=response_status),
        )
        update_session_patch = mocker.patch(
            "authentication.views.update_session_auth_hash", return_value=mocker.Mock()
        )
        client.force_login(user)
        client.post(reverse("set-password-api"), {})
        assert update_session_patch.called is expected_session_update


def test_get_social_auth_types(client, user):
    """Verify that get_social_auth_types returns a list of providers that the user has authenticated with"""
    social_auth_providers = ["provider1", "provider2"]
    url = reverse("get-auth-types-api")
    UserSocialAuthFactory.create_batch(
        2, user=user, provider=factory.Iterator(social_auth_providers)
    )
    client.force_login(user)
    resp = client.get(url)
    assert resp.json() == [{"provider": provider} for provider in social_auth_providers]
