"""Fixtures that will be used by default"""
import pytest


@pytest.fixture(autouse=True)
def patch_create_courseware_user_signal(request, mocker):
    """Patches the _create_courseware_user that is called after user creation"""
    if "no_create_courseware_user_fixture" in request.keywords:
        return
    # patch the transaction on_commit so it immediately invokes the callback
    mocker.patch(
        "courseware.signals.transaction.on_commit",
        side_effect=lambda callback: callback(),
    )

    # patch the method being called
    patched = mocker.patch("courseware.signals._create_courseware_user")
    return patched


@pytest.fixture(autouse=True)
def disable_hubspot_api(settings):
    """Disable Hubspot API by default for tests"""
    settings.HUBSPOT_API_KEY = None
