"""Project conftest"""
import pytest


@pytest.fixture(autouse=True)
def default_settings(settings):
    """Set default settings for all tests"""
    settings.DISABLE_WEBPACK_LOADER_STATS = True
