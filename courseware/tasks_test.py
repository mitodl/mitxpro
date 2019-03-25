"""Courseware tasks"""
import pytest
from users.factories import UserFactory

from courseware import tasks


@pytest.mark.django_db
def test_create_edx_user_from_id(mocker):
    """Test that create_edx_user_from_id loads a user and calls the API method to create an edX user"""
    patch_create_edx_user = mocker.patch("courseware.tasks.create_edx_user")
    user = UserFactory.create()
    tasks.create_edx_user_from_id.delay(user.id)
    patch_create_edx_user.assert_called_once_with(user)
