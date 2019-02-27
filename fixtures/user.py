"""User related fixtures"""
import pytest

from users.factories import UserFactory

# pylint: disable=redefined-outer-name


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """Creates a user"""
    return UserFactory.create()


@pytest.fixture
def user_client(client, user):
    """Version of the client that is authenticated with the user"""
    client.force_login(user)
    return client
