"""API tests"""
import pytest
from django.db import IntegrityError

from authentication import api
from users.factories import UserFactory
from users.serializers import UserSerializer

pytestmark = pytest.mark.django_db


def test_create_user_session(user):
    """Test that we get a session cookie out of create_user_session"""
    session = api.create_user_session(user)
    assert session is not None
    assert session.session_key is not None


def test_create_user_with_generated_username(mocker, valid_address_dict):
    """
    Integration test to assert that create_user_with_generated_username tries to find an available
    username and try again to save a User if there was a username collision
    """
    username = "testuser"
    # Create a user with the desired username before calling the function so we get a collision
    UserFactory.create(username=username)
    data = {
        "username": username,
        "email": "test@example.com",
        "name": "Test User",
        "legal_address": valid_address_dict,
        "password": "fakepassword",
    }
    serializer = UserSerializer(data=data)
    serializer.is_valid()
    patched_find_username = mocker.patch(
        "authentication.api.find_available_username", return_value="testuser1"
    )

    created_user = api.create_user_with_generated_username(serializer, username)
    patched_find_username.assert_called_once_with(username)
    assert created_user is not None
    assert created_user.username == patched_find_username.return_value


def test_create_user_reattempt(mocker):
    """
    Test that create_user_with_generated_username reattempts User creation multiple times when
    username collisions are experienced repeatedly
    """
    username = "testuser"
    fake_user = UserFactory.build()
    patched_find_username = mocker.patch(
        "authentication.api.find_available_username",
        side_effect=["testuser1", "testuser2", "testuser3"],
    )
    patched_save = mocker.patch.object(
        UserSerializer,
        "save",
        side_effect=[
            IntegrityError("(username)=(testuser) already exists"),
            IntegrityError("(username)=(testuser1) already exists"),
            IntegrityError("(username)=(testuser2) already exists"),
            fake_user,
        ],
    )

    created_user = api.create_user_with_generated_username(
        UserSerializer(data={}), username
    )
    assert patched_save.call_count == 4
    patched_save.assert_any_call(username="testuser")
    patched_save.assert_any_call(username="testuser1")
    patched_save.assert_any_call(username="testuser2")
    patched_save.assert_any_call(username="testuser3")
    # `find_available_username` should be called as many times as serializer.save() failed
    # with a duplicate username error
    assert patched_find_username.call_count == 3
    patched_find_username.assert_called_with(username)
    assert created_user == fake_user


def test_create_user_too_many_attempts(mocker):
    """
    Test that create_user_with_generated_username exits if there are too many attempts
    """
    attempt_limit = 2
    mocker.patch("authentication.api.USERNAME_COLLISION_ATTEMPTS", attempt_limit)
    patched_save = mocker.patch.object(
        UserSerializer,
        "save",
        side_effect=(IntegrityError("(username)=(testuser) already exists")),
    )
    patched_find_username = mocker.patch(
        "authentication.api.find_available_username", return_value=None
    )
    created_user = api.create_user_with_generated_username(
        UserSerializer(data={}), "testuser"
    )
    assert created_user is None
    assert patched_save.call_count == attempt_limit
    assert patched_find_username.call_count == attempt_limit


def test_create_user_exception(mocker):
    """
    Test that create_user_with_generated_username does not reattempt if an exception was raised that
    does not indicate a username collision
    """
    patched_save = mocker.patch.object(
        UserSerializer, "save", side_effect=ValueError("idk")
    )
    with pytest.raises(ValueError):
        api.create_user_with_generated_username(UserSerializer(data={}), "testuser")
    patched_save.assert_called_once()
