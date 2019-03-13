"""Project conftest"""
# pylint: disable=wildcard-import, unused-wildcard-import
import pytest
from fixtures.common import *


@pytest.fixture(autouse=True)
def default_settings(settings):
    """Set default settings for all tests"""
    settings.DISABLE_WEBPACK_LOADER_STATS = True
    settings.MITXPRO_BASE_URL = "http://localhost:8053/"
