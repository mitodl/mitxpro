"""Fixtures that will be used by default"""
import pytest


@pytest.fixture(autouse=True)
def disable_hubspot_api(settings):
    """Disable Hubspot API by default for tests"""
    settings.HUBSPOT_API_KEY = None
