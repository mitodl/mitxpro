"""API tests"""

import pytest

from authentication import api

pytestmark = pytest.mark.django_db


def test_create_user_session(user):
    """Test that we get a session cookie out of create_user_session"""
    session = api.create_user_session(user)
    assert session is not None
    assert session.session_key is not None
