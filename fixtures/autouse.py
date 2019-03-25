"""Fixtures that will be used by default"""
import pytest


@pytest.fixture(autouse=True)
def patch_create_edx_user_task(mocker):
    """Patches the create_edx_user_from_id task that is called after user creation"""
    patched = mocker.patch("users.models.create_edx_user_from_id")
    return patched
