"""Project conftest"""
import pytest

# pylint: disable=wildcard-import,unused-wildcard-import
from fixtures.user import *


@pytest.fixture(autouse=True)
def default_settings(settings):
    """Set default settings for all tests"""
    settings.DISABLE_WEBPACK_LOADER_STATS = True
    settings.MITXPRO_BASE_URL = "http://localhost:8053/"
