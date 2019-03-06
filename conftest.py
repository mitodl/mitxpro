"""Project conftest"""
import pytest


@pytest.fixture(autouse=True)
def disable_webpack(settings):
    """Disable webpack loader for all tests"""
    settings.DISABLE_WEBPACK_LOADER_STATS = True
