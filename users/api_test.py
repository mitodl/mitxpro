"""Tests for user api"""
from users.api import get_user_by_id


def test_get_user_by_id(user):
    """Tests get_user_by_id"""
    assert get_user_by_id(user.id) == user
