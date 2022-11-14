"""Fixtures that will be used by default"""
import pytest


@pytest.fixture(autouse=True)
def disable_hubspot_api(settings):
    """Disable Hubspot API by default for tests"""
    settings.MITOL_HUBSPOT_API_PRIVATE_TOKEN = None
