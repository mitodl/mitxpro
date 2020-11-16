"""Tests for authentication views"""
# pylint: disable=redefined-outer-name
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.core import mail
from django.db import transaction
from django.urls import reverse
from django.test import Client, override_settings
import factory
from faker import Faker
from hypothesis import settings as hypothesis_settings, strategies as st, Verbosity
from hypothesis.stateful import (
    consumes,
    precondition,
    rule,
    Bundle,
    RuleBasedStateMachine,
    HealthCheck,
)
from hypothesis.extra.django import TestCase as HTestCase
import pytest
import responses
from rest_framework import status
from social_core.backends.email import EmailAuth

from authentication.serializers import PARTIAL_PIPELINE_TOKEN_KEY
from authentication.utils import SocialAuthState
from compliance.constants import RESULT_DENIED, RESULT_SUCCESS
from compliance.models import ExportsInquiryLog
from compliance.test_utils import (
    get_cybersource_test_settings,
    mock_cybersource_wsdl,
    mock_cybersource_wsdl_operation,
)
from users.factories import UserFactory, UserSocialAuthFactory
from mitxpro.test_utils import any_instance_of, MockResponse

pytestmark = [pytest.mark.django_db]

NEW_EMAIL = "test@example.com"
NEXT_URL = "/next/url"

User = get_user_model()

fake = Faker()

# pylint: disable=too-many-public-methods


@pytest.fixture
def email_user(user):
    """Fixture for a user that has an 'email' type UserSocialAuth"""
    UserSocialAuthFactory.create(user=user, provider=EmailAuth.name, uid=user.email)
    return user


# pylint: disable=too-many-arguments
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
        "field_errors": {},
        "redirect_url": None,
        "extra_data": {},
        "state": None,
        "provider": EmailAuth.name,
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


@contextmanager
def noop():
    """A no-op context manager"""
    yield


@contextmanager
def export_check_response(response_name):
    """Context manager for configuring export check responses"""
    with override_settings(
        **get_cybersource_test_settings()
    ), responses.RequestsMock() as mocked_responses:
        mock_cybersource_wsdl(mocked_responses, settings)
        mock_cybersource_wsdl_operation(mocked_responses, response_name)
        yield


class AuthStateMachine(RuleBasedStateMachine):
    """
    State machine for auth flows

    How to understand this code:

    This code exercises our social auth APIs, which is basically a graph of nodes and edges that the user traverses.
    You can understand the bundles defined below to be the nodes and the methods of this class to be the edges.

    If you add a new state to the auth flows, create a new bundle to represent that state and define
    methods to define transitions into and (optionally) out of that state.
    """

    # pylint: disable=too-many-instance-attributes

    ConfirmationSentAuthStates = Bundle("confirmation-sent")
    ConfirmationRedeemedAuthStates = Bundle("confirmation-redeemed")
    RegisterExtraDetailsAuthStates = Bundle("register-details-extra")

    LoginPasswordAuthStates = Bundle("login-password")
    LoginPasswordAbandonedAuthStates = Bundle("login-password-abandoned")

    recaptcha_patcher = patch(
        "authentication.views.requests.post",
        return_value=MockResponse(
            content='{"success": true}', status_code=status.HTTP_200_OK
        ),
    )
    email_send_patcher = patch(
        "mail.verification_api.send_verification_email", autospec=True
    )
    courseware_api_patcher = patch("authentication.pipeline.user.courseware_api")
    courseware_tasks_patcher = patch("authentication.pipeline.user.courseware_tasks")

    def __init__(self):
        """Setup the machine"""
        super().__init__()
        # wrap the execution in a django transaction, similar to django's TestCase
        self.atomic = transaction.atomic()
        self.atomic.__enter__()

        # wrap the execution in a patch()
        self.mock_email_send = self.email_send_patcher.start()
        self.mock_courseware_api = self.courseware_api_patcher.start()
        self.mock_courseware_tasks = self.courseware_tasks_patcher.start()

        # django test client
        self.client = Client()

        # shared data
        self.email = fake.email()
        self.user = None
        self.password = "password123"

        # track whether we've hit an action that starts a flow or not
        self.flow_started = False

    def teardown(self):
        """Cleanup from a run"""
        # clear the mailbox
        del mail.outbox[:]

        # stop the patches
        self.email_send_patcher.stop()
        self.courseware_api_patcher.stop()
        self.courseware_tasks_patcher.stop()

        # end the transaction with a rollback to cleanup any state
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

    def create_existing_user(self):
        """Create an existing user"""
        self.user = UserFactory.create(email=self.email)
        self.user.set_password(self.password)
        self.user.save()
        UserSocialAuthFactory.create(
            user=self.user, provider=EmailAuth.name, uid=self.user.email
        )

    @rule(
        target=ConfirmationSentAuthStates,
        recaptcha_enabled=st.sampled_from([True, False]),
    )
    @precondition(lambda self: not self.flow_started)
    def register_email_not_exists(self, recaptcha_enabled):
        """Register email not exists"""
        self.flow_started = True

        with ExitStack() as stack:
            mock_recaptcha_success = None
            if recaptcha_enabled:
                mock_recaptcha_success = stack.enter_context(self.recaptcha_patcher)
                stack.enter_context(override_settings(**{"RECAPTCHA_SITE_KEY": "fake"}))
            result = assert_api_call(
                self.client,
                "psa-register-email",
                {
                    "flow": SocialAuthState.FLOW_REGISTER,
                    "email": self.email,
                    **({"recaptcha": "fake"} if recaptcha_enabled else {}),
                },
                {
                    "flow": SocialAuthState.FLOW_REGISTER,
                    "partial_token": None,
                    "state": SocialAuthState.STATE_REGISTER_CONFIRM_SENT,
                },
            )
            self.mock_email_send.assert_called_once()
            if mock_recaptcha_success:
                mock_recaptcha_success.assert_called_once()
            return result

    @rule(
        target=LoginPasswordAuthStates, recaptcha_enabled=st.sampled_from([True, False])
    )
    @precondition(lambda self: not self.flow_started)
    def register_email_exists(self, recaptcha_enabled):
        """Register email exists"""
        self.flow_started = True
        self.create_existing_user()

        with ExitStack() as stack:
            mock_recaptcha_success = None
            if recaptcha_enabled:
                mock_recaptcha_success = stack.enter_context(self.recaptcha_patcher)
                stack.enter_context(override_settings(**{"RECAPTCHA_SITE_KEY": "fake"}))

            result = assert_api_call(
                self.client,
                "psa-register-email",
                {
                    "flow": SocialAuthState.FLOW_REGISTER,
                    "email": self.email,
                    "next": NEXT_URL,
                    **({"recaptcha": "fake"} if recaptcha_enabled else {}),
                },
                {
                    "flow": SocialAuthState.FLOW_REGISTER,
                    "state": SocialAuthState.STATE_LOGIN_PASSWORD,
                    "errors": ["Password is required to login"],
                },
            )
            self.mock_email_send.assert_not_called()
            if mock_recaptcha_success:
                mock_recaptcha_success.assert_called_once()
            return result

    @rule()
    @precondition(lambda self: not self.flow_started)
    def register_email_not_exists_with_recaptcha_invalid(self):
        """Yield a function for this step"""
        self.flow_started = True
        with patch(
            "authentication.views.requests.post",
            return_value=MockResponse(
                content='{"success": false, "error-codes": ["bad-request"]}',
                status_code=status.HTTP_200_OK,
            ),
        ) as mock_recaptcha_failure, override_settings(
            **{"RECAPTCHA_SITE_KEY": "fakse"}
        ):
            assert_api_call(
                self.client,
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
            self.mock_email_send.assert_not_called()

    @rule()
    @precondition(lambda self: not self.flow_started)
    def login_email_not_exists(self):
        """Login for an email that doesn't exist"""
        self.flow_started = True
        assert_api_call(
            self.client,
            "psa-login-email",
            {"flow": SocialAuthState.FLOW_LOGIN, "email": self.email},
            {
                "field_errors": {"email": "Couldn't find your account"},
                "flow": SocialAuthState.FLOW_LOGIN,
                "partial_token": None,
                "state": SocialAuthState.STATE_REGISTER_REQUIRED,
            },
        )
        assert User.objects.filter(email=self.email).exists() is False

    @rule(target=LoginPasswordAuthStates)
    @precondition(lambda self: not self.flow_started)
    def login_email_exists(self):
        """Login with a user that exists"""
        self.flow_started = True
        self.create_existing_user()

        return assert_api_call(
            self.client,
            "psa-login-email",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "email": self.user.email,
                "next": NEXT_URL,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "state": SocialAuthState.STATE_LOGIN_PASSWORD,
                "extra_data": {"name": self.user.name},
            },
        )

    @rule(
        target=LoginPasswordAbandonedAuthStates,
        auth_state=consumes(RegisterExtraDetailsAuthStates),
    )
    @precondition(lambda self: self.flow_started)
    def login_email_abandoned(self, auth_state):  # pylint: disable=unused-argument
        """Login with a user that abandoned the register flow"""
        # NOTE: This works by "consuming" an extra details auth state,
        #       but discarding the state and starting a new login.
        #       It then re-targets the new state into the extra details again.
        auth_state = None  # assign None to ensure no accidental usage here

        return assert_api_call(
            self.client,
            "psa-login-email",
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "email": self.user.email,
                "next": NEXT_URL,
            },
            {
                "flow": SocialAuthState.FLOW_LOGIN,
                "state": SocialAuthState.STATE_LOGIN_PASSWORD,
                "extra_data": {"name": self.user.name},
            },
        )

    @rule(
        target=RegisterExtraDetailsAuthStates,
        auth_state=consumes(LoginPasswordAbandonedAuthStates),
    )
    def login_password_abandoned(self, auth_state):
        """Login with an abandoned registration user"""
        return assert_api_call(
            self.client,
            "psa-login-password",
            {
                "flow": auth_state["flow"],
                "partial_token": auth_state["partial_token"],
                "password": self.password,
            },
            {
                "flow": auth_state["flow"],
                "state": SocialAuthState.STATE_REGISTER_EXTRA_DETAILS,
            },
        )

    @rule(auth_state=consumes(LoginPasswordAuthStates))
    def login_password_valid(self, auth_state):
        """Login with a valid password"""
        assert_api_call(
            self.client,
            "psa-login-password",
            {
                "flow": auth_state["flow"],
                "partial_token": auth_state["partial_token"],
                "password": self.password,
            },
            {
                "flow": auth_state["flow"],
                "redirect_url": NEXT_URL,
                "partial_token": None,
                "state": SocialAuthState.STATE_SUCCESS,
            },
            expect_authenticated=True,
        )

    @rule(target=LoginPasswordAuthStates, auth_state=consumes(LoginPasswordAuthStates))
    def login_password_invalid(self, auth_state):
        """Login with an invalid password"""
        return assert_api_call(
            self.client,
            "psa-login-password",
            {
                "flow": auth_state["flow"],
                "partial_token": auth_state["partial_token"],
                "password": "invalidpass",
            },
            {
                "field_errors": {
                    "password": "Unable to login with that email and password combination"
                },
                "flow": auth_state["flow"],
                "state": SocialAuthState.STATE_ERROR,
            },
        )

    @rule(
        auth_state=consumes(LoginPasswordAuthStates),
        verify_exports=st.sampled_from([True, False]),
    )
    def login_password_user_inactive(self, auth_state, verify_exports):
        """Login for an inactive user"""
        self.user.is_active = False
        self.user.save()

        cm = export_check_response("100_success") if verify_exports else noop()

        with cm:
            assert_api_call(
                self.client,
                "psa-login-password",
                {
                    "flow": auth_state["flow"],
                    "partial_token": auth_state["partial_token"],
                    "password": self.password,
                },
                {
                    "flow": auth_state["flow"],
                    "redirect_url": NEXT_URL,
                    "partial_token": None,
                    "state": SocialAuthState.STATE_SUCCESS,
                },
                expect_authenticated=True,
            )

    @rule(auth_state=consumes(LoginPasswordAuthStates))
    def login_password_exports_temporary_error(self, auth_state):
        """Login for a user who hasn't been OFAC verified yet"""
        with override_settings(**get_cybersource_test_settings()), patch(
            "authentication.pipeline.compliance.api.verify_user_with_exports",
            side_effect=Exception("register_details_export_temporary_error"),
        ):
            assert_api_call(
                self.client,
                "psa-login-password",
                {
                    "flow": auth_state["flow"],
                    "partial_token": auth_state["partial_token"],
                    "password": self.password,
                },
                {
                    "flow": auth_state["flow"],
                    "partial_token": None,
                    "state": SocialAuthState.STATE_ERROR_TEMPORARY,
                    "errors": [
                        "Unable to register at this time, please try again later"
                    ],
                },
            )

    @rule(
        target=ConfirmationRedeemedAuthStates,
        auth_state=consumes(ConfirmationSentAuthStates),
    )
    def redeem_confirmation_code(self, auth_state):
        """Redeem a registration confirmation code"""
        _, _, code, partial_token = self.mock_email_send.call_args[0]
        return assert_api_call(
            self.client,
            "psa-register-confirm",
            {
                "flow": auth_state["flow"],
                "verification_code": code.code,
                "partial_token": partial_token,
            },
            {
                "flow": auth_state["flow"],
                "state": SocialAuthState.STATE_REGISTER_DETAILS,
            },
        )

    @rule(auth_state=consumes(ConfirmationRedeemedAuthStates))
    def redeem_confirmation_code_twice(self, auth_state):
        """Redeeming a code twice should fail"""
        _, _, code, partial_token = self.mock_email_send.call_args[0]
        assert_api_call(
            self.client,
            "psa-register-confirm",
            {
                "flow": auth_state["flow"],
                "verification_code": code.code,
                "partial_token": partial_token,
            },
            {
                "errors": [],
                "flow": auth_state["flow"],
                "redirect_url": None,
                "partial_token": None,
                "state": SocialAuthState.STATE_INVALID_LINK,
            },
        )

    @rule(auth_state=consumes(ConfirmationRedeemedAuthStates))
    def redeem_confirmation_code_twice_existing_user(self, auth_state):
        """Redeeming a code twice with an existing user should fail with existing account state"""
        _, _, code, partial_token = self.mock_email_send.call_args[0]
        self.create_existing_user()
        assert_api_call(
            self.client,
            "psa-register-confirm",
            {
                "flow": auth_state["flow"],
                "verification_code": code.code,
                "partial_token": partial_token,
            },
            {
                "errors": [],
                "flow": auth_state["flow"],
                "redirect_url": None,
                "partial_token": None,
                "state": SocialAuthState.STATE_EXISTING_ACCOUNT,
            },
        )

    @rule(
        target=RegisterExtraDetailsAuthStates,
        auth_state=consumes(ConfirmationRedeemedAuthStates),
    )
    def register_details(self, auth_state):
        """Complete the register confirmation details page"""
        result = assert_api_call(
            self.client,
            "psa-register-details",
            {
                "flow": auth_state["flow"],
                "partial_token": auth_state["partial_token"],
                "password": self.password,
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
                "flow": auth_state["flow"],
                "state": SocialAuthState.STATE_REGISTER_EXTRA_DETAILS,
            },
        )
        self.user = User.objects.get(email=self.email)
        return result

    @rule(
        target=RegisterExtraDetailsAuthStates,
        auth_state=consumes(ConfirmationRedeemedAuthStates),
    )
    def register_details_export_success(self, auth_state):
        """Complete the register confirmation details page with exports enabled"""
        with export_check_response("100_success"):
            result = assert_api_call(
                self.client,
                "psa-register-details",
                {
                    "flow": auth_state["flow"],
                    "partial_token": auth_state["partial_token"],
                    "password": self.password,
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
                    "flow": auth_state["flow"],
                    "state": SocialAuthState.STATE_REGISTER_EXTRA_DETAILS,
                },
            )
            assert ExportsInquiryLog.objects.filter(user__email=self.email).exists()
            assert (
                ExportsInquiryLog.objects.get(user__email=self.email).computed_result
                == RESULT_SUCCESS
            )
            assert len(mail.outbox) == 0

            self.user = User.objects.get(email=self.email)
            return result

    @rule(auth_state=consumes(ConfirmationRedeemedAuthStates))
    def register_details_export_reject(self, auth_state):
        """Complete the register confirmation details page with exports enabled"""
        with export_check_response("700_reject"):
            assert_api_call(
                self.client,
                "psa-register-details",
                {
                    "flow": auth_state["flow"],
                    "partial_token": auth_state["partial_token"],
                    "password": self.password,
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
                    "flow": auth_state["flow"],
                    "partial_token": None,
                    "errors": ["Error code: CS_700"],
                    "state": SocialAuthState.STATE_USER_BLOCKED,
                },
            )
            assert ExportsInquiryLog.objects.filter(user__email=self.email).exists()
            assert (
                ExportsInquiryLog.objects.get(user__email=self.email).computed_result
                == RESULT_DENIED
            )
            assert len(mail.outbox) == 1

    @rule(auth_state=consumes(ConfirmationRedeemedAuthStates))
    def register_details_export_temporary_error(self, auth_state):
        """Complete the register confirmation details page with exports raising a temporary error"""
        with override_settings(**get_cybersource_test_settings()), patch(
            "authentication.pipeline.compliance.api.verify_user_with_exports",
            side_effect=Exception("register_details_export_temporary_error"),
        ):
            assert_api_call(
                self.client,
                "psa-register-details",
                {
                    "flow": auth_state["flow"],
                    "partial_token": auth_state["partial_token"],
                    "password": self.password,
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
                    "flow": auth_state["flow"],
                    "partial_token": None,
                    "errors": [
                        "Unable to register at this time, please try again later"
                    ],
                    "state": SocialAuthState.STATE_ERROR_TEMPORARY,
                },
            )
            assert not ExportsInquiryLog.objects.filter(user__email=self.email).exists()
            assert len(mail.outbox) == 0

    @rule(auth_state=consumes(RegisterExtraDetailsAuthStates))
    def register_user_extra_details(self, auth_state):
        """Complete the user's extra details"""
        assert_api_call(
            Client(),
            "psa-register-extra",
            {
                "flow": auth_state["flow"],
                "partial_token": auth_state["partial_token"],
                "gender": "f",
                "birth_year": "2000",
                "company": "MIT",
                "job_title": "QA Manager",
            },
            {
                "flow": auth_state["flow"],
                "state": SocialAuthState.STATE_SUCCESS,
                "partial_token": None,
            },
            expect_authenticated=True,
        )


AuthStateMachine.TestCase.settings = hypothesis_settings(
    max_examples=100,
    stateful_step_count=10,
    deadline=None,
    verbosity=Verbosity.normal,
    suppress_health_check=[HealthCheck.filter_too_much],
)


class AuthStateTestCase(HTestCase, AuthStateMachine.TestCase):
    """TestCase for AuthStateMachine"""


@pytest.mark.usefixtures("mock_email_send")
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
        "field_errors": {},
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


def test_well_known_openid_configuration(client):
    """Test that .well-known/openid-configuration returns the right data"""
    resp = client.get("/.well-known/openid-configuration")
    assert resp.json() == {
        "issuer": "http://localhost:8053",
        "authorization_endpoint": "http://localhost:8053/oauth2/authorize/",
        "token_endpoint": "http://localhost:8053/oauth2/token/",
    }
