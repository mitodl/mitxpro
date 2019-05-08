"""Tests of user pipeline actions"""
# pylint: disable=redefined-outer-name

from django.contrib.sessions.middleware import SessionMiddleware
import pytest
from social_core.backends.email import EmailAuth
from social_django.utils import load_strategy, load_backend

from users.factories import UserFactory
from authentication.pipeline import user as user_actions
from authentication.exceptions import (
    InvalidPasswordException,
    RequirePasswordException,
    RequireRegistrationException,
    RequirePasswordAndAddressException,
    UnexpectedExistingUserException,
    RequireProfileException,
)
from authentication.utils import SocialAuthState


@pytest.fixture
def backend_settings(settings):
    """A dictionary of settings for the backend"""
    return {"USER_FIELDS": settings.SOCIAL_AUTH_EMAIL_USER_FIELDS}


@pytest.fixture
def mock_email_backend(mocker, backend_settings):
    """Fixture that returns a fake EmailAuth backend object"""
    backend = mocker.Mock()
    backend.name = "email"
    backend.setting.side_effect = lambda key, default, **kwargs: backend_settings.get(
        key, default
    )
    return backend


@pytest.fixture
def mock_create_user_strategy(mocker):
    """Fixture that returns a valid strategy for create_user_via_email"""
    strategy = mocker.Mock()
    strategy.request_data.return_value = {
        "name": "Jane Doe",
        "password": "password1",
        "legal_address": {
            "first_name": "Jane",
            "last_name": "Doe",
            "street_address_1": "1 Main st",
            "city": "Boston",
            "state_or_territory": "US-MA",
            "country": "US",
            "postal_code": "02101",
        },
    }
<<<<<<< HEAD
=======
    return strategy


@pytest.fixture
def mock_create_profile_strategy(mocker):
    """Fixture that returns a valid strategy for create_profile_via_email"""
    strategy = mocker.Mock()
    strategy.request_data.return_value = {
        "gender": "f",
        "birth_year": "2000",
        "company": "MIT",
        "job_title": "QA Tester",
    }
>>>>>>> Registration form step 2
    return strategy


def validate_email_auth_request_not_email_backend(mocker):
    """Tests that validate_email_auth_request return if not using the email backend"""
    mock_strategy = mocker.Mock()
    mock_backend = mocker.Mock()
    mock_backend.name = "notemail"
    assert user_actions.validate_email_auth_request(mock_strategy, mock_backend) == {}


@pytest.mark.parametrize(
    "has_user,expected", [(True, {"flow": SocialAuthState.FLOW_LOGIN}), (False, {})]
)
@pytest.mark.django_db
def test_validate_email_auth_request(rf, has_user, expected):
    """Test that validate_email_auth_request returns correctly given the input"""
    request = rf.post("/complete/email")
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    strategy = load_strategy(request)
    backend = load_backend(strategy, "email", None)

    user = UserFactory.create() if has_user else None

    assert (
        user_actions.validate_email_auth_request(
            strategy, backend, pipeline_index=0, user=user
        )
        == expected
    )


def test_get_username(mocker, user):
    """Tests that we get a username for a new user"""
    mock_strategy = mocker.Mock()
    mock_strategy.storage.user.get_username.return_value = user.username
    assert user_actions.get_username(mock_strategy, None, user) == {
        "username": user.username
    }
    mock_strategy.storage.user.get_username.assert_called_once_with(user)


def test_get_username_no_user(mocker):
    """Tests that we get a username for a new user"""
    mock_strategy = mocker.Mock()
    assert user_actions.get_username(mock_strategy, None, None)["username"] is not None
    mock_strategy.storage.user.get_username.assert_not_called()


def test_user_password_not_email_backend(mocker):
    """Tests that user_password return if not using the email backend"""
    mock_strategy = mocker.MagicMock()
    mock_user = mocker.Mock()
    mock_backend = mocker.Mock()
    mock_backend.name = "notemail"
    assert (
        user_actions.validate_password(
            mock_strategy,
            mock_backend,
            pipeline_index=0,
            user=mock_user,
            flow=SocialAuthState.FLOW_LOGIN,
        )
        == {}
    )
    # make sure we didn't update or check the password
    mock_user.set_password.assert_not_called()
    mock_user.save.assert_not_called()
    mock_user.check_password.assert_not_called()


@pytest.mark.parametrize("user_password", ["abc123", "def456"])
def test_user_password_login(rf, user, user_password):
    """Tests that user_password works for login case"""
    request_password = "abc123"
    user.set_password(user_password)
    user.save()
    request = rf.post(
        "/complete/email", {"password": request_password, "email": user.email}
    )
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    strategy = load_strategy(request)
    backend = load_backend(strategy, "email", None)

    if request_password == user_password:
        assert (
            user_actions.validate_password(
                strategy,
                backend,
                pipeline_index=0,
                user=user,
                flow=SocialAuthState.FLOW_LOGIN,
            )
            == {}
        )
    else:
        with pytest.raises(InvalidPasswordException):
            user_actions.validate_password(
                strategy,
                backend,
                pipeline_index=0,
                user=user,
                flow=SocialAuthState.FLOW_LOGIN,
            )


def test_user_password_not_login(rf, user):
    """
    Tests that user_password performs denies authentication
    for an existing user if password not provided regardless of auth_type
    """
    user.set_password("abc123")
    user.save()
    request = rf.post("/complete/email", {"email": user.email})
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    strategy = load_strategy(request)
    backend = load_backend(strategy, "email", None)

    with pytest.raises(RequirePasswordException):
        user_actions.validate_password(
            strategy,
            backend,
            pipeline_index=0,
            user=user,
            flow=SocialAuthState.FLOW_LOGIN,
        )


def test_user_password_not_exists(rf):
    """Tests that user_password raises auth error for nonexistent user"""
    request = rf.post(
        "/complete/email", {"password": "abc123", "email": "doesntexist@localhost"}
    )
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    strategy = load_strategy(request)
    backend = load_backend(strategy, "email", None)

    with pytest.raises(RequireRegistrationException):
        user_actions.validate_password(
            strategy,
            backend,
            pipeline_index=0,
            user=None,
            flow=SocialAuthState.FLOW_LOGIN,
        )


@pytest.mark.parametrize(
    "backend_name,flow",
    [
        ("notemail", None),
        ("notemail", SocialAuthState.FLOW_REGISTER),
        ("notemail", SocialAuthState.FLOW_LOGIN),
        (EmailAuth.name, None),
        (EmailAuth.name, SocialAuthState.FLOW_LOGIN),
    ],
)
def test_create_user_via_email_exit(mocker, backend_name, flow):
    """
    Tests that create_user_via_email returns if not using the email backend and attempting the
    'register' step of the auth flow
    """
    mock_strategy = mocker.Mock()
    mock_backend = mocker.Mock()
    mock_backend.name = backend_name
    assert (
        user_actions.create_user_via_email(
            mock_strategy, mock_backend, pipeline_index=0, flow=flow
        )
        == {}
    )

    mock_strategy.request_data.assert_not_called()


@pytest.mark.django_db
def test_create_user_via_email(mock_email_backend, mock_create_user_strategy):
    """
    Tests that create_user_via_email creates a user via social_core.pipeline.user.create_user_via_email
    and sets a name and password
    """
    username = "abc"
    email = "user@example.com"
    response = user_actions.create_user_via_email(
        mock_create_user_strategy,
        mock_email_backend,
        details=dict(username=username, email=email),
        pipeline_index=0,
        flow=SocialAuthState.FLOW_REGISTER,
    )
    assert "user" in response
    assert response["user"].username == username
    assert response["user"].email == email
    assert response["user"].name == mock_create_user_strategy.request_data()["name"]
    assert response["user"].check_password(
        mock_create_user_strategy.request_data()["password"]
    )


@pytest.mark.django_db
def test_create_user_via_email_no_data(mocker, mock_email_backend):
    """Tests that create_user_via_email raises an error if no data for name and password provided"""
    mock_strategy = mocker.Mock()
    mock_strategy.request_data.return_value = {}
    with pytest.raises(RequirePasswordAndAddressException):
        user_actions.create_user_via_email(
            mock_strategy,
            mock_email_backend,
            pipeline_index=0,
            flow=SocialAuthState.FLOW_REGISTER,
        )


@pytest.mark.django_db
def test_create_user_via_email_existing_user_raises(
    user, mock_email_backend, mock_create_user_strategy
):
    """Tests that create_user_via_email raises an error if a user already exists in the pipeline"""
    with pytest.raises(UnexpectedExistingUserException):
        user_actions.create_user_via_email(
            mock_create_user_strategy,
            mock_email_backend,
            user=user,
            pipeline_index=0,
            flow=SocialAuthState.FLOW_REGISTER,
        )


@pytest.mark.django_db
def test_create_profile_via_email(
    mock_email_backend, mock_create_profile_strategy, user
):
    """
    Tests that create_profile_via_email creates a profile
    """
    response = user_actions.create_profile_via_email(
        mock_create_profile_strategy,
        mock_email_backend,
        user=user,
        pipeline_index=0,
        flow=SocialAuthState.FLOW_REGISTER,
    )
    assert response == {}
    assert user.profile.gender == mock_create_profile_strategy.request_data().get(
        "gender"
    )
    assert user.profile.company == mock_create_profile_strategy.request_data().get(
        "company"
    )


@pytest.mark.django_db
def test_create_profile_via_email_no_data(mocker, mock_email_backend):
    """Tests that create_profile_via_email raises an error if no data for name and password provided"""
    mock_strategy = mocker.Mock()
    mock_strategy.request_data.return_value = {}
    with pytest.raises(RequireProfileException):
        user_actions.create_profile_via_email(
            mock_strategy,
            mock_email_backend,
            pipeline_index=0,
            flow=SocialAuthState.FLOW_REGISTER,
        )


@pytest.mark.parametrize("hijacked", [True, False])
def test_forbid_hijack(mocker, hijacked):
    """
    Tests that forbid_hijack action raises an exception if a user is hijacked
    """
    mock_strategy = mocker.Mock()
    mock_strategy.session_get.return_value = hijacked

    mock_backend = mocker.Mock(name="email")

    args = [mock_strategy, mock_backend]
    kwargs = {"flow": SocialAuthState.FLOW_LOGIN}

    if hijacked:
        with pytest.raises(ValueError):
            user_actions.forbid_hijack(*args, **kwargs)
    else:
        assert user_actions.forbid_hijack(*args, **kwargs) == {}
