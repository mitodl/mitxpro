"""API tests"""
import pytest

from django.contrib.auth import get_user_model

from authentication import api

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_create_user():
    """Tests that a user and associated objects are created"""
    email = "email@localhost"
    username = "username"
    user = api.create_user(username, email, {"name": "Bob"})

    assert isinstance(user, User)
    assert user.email == email
    assert user.username == username
    assert user.name == "Bob"
