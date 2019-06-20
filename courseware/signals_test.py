"""Tests for courseware signals"""
import pytest

from users.models import User


@pytest.fixture(autouse=True)
def patch_on_commit(mocker):
    """Patch on_commit so it executes immediately"""
    return mocker.patch(
        "courseware.signals.transaction.on_commit",
        side_effect=lambda callback: callback(),
    )


@pytest.mark.no_create_courseware_user_fixture
@pytest.mark.django_db
def test_courseware(mocker):
    """Test that the signal for user creation is triggered correctly"""
    patched_create_user_api = mocker.patch("courseware.api.create_user")
    patched_create_user_task = mocker.patch("courseware.tasks.create_user_from_id")

    user = User.objects.create(email="user@localhost")

    patched_create_user_api.assert_called_once_with(user)
    patched_create_user_task.apply_async.assert_not_called()


@pytest.mark.no_create_courseware_user_fixture
@pytest.mark.django_db
def test_courseware_error(mocker):
    """Test that a failure in the API causes an async task to be triggered"""
    patched_create_user_api = mocker.patch(
        "courseware.api.create_user", side_effect=Exception("error")
    )
    patched_create_user_task = mocker.patch("courseware.tasks.create_user_from_id")

    user = User.objects.create(email="user@localhost")

    patched_create_user_api.assert_called_once_with(user)
    patched_create_user_task.apply_async.assert_called_once_with(
        (user.id,), countdown=60
    )
