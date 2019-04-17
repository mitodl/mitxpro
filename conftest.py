"""Project conftest"""
# pylint: disable=wildcard-import,unused-wildcard-import
import shutil
import pytest
from django.conf import settings

from fixtures.common import *
from fixtures.autouse import *


TEST_MEDIA_ROOT = "/var/media/test_media_root"


def pytest_configure():
    """Pytest hook to perform some initial configuration"""
    settings.MEDIA_ROOT = TEST_MEDIA_ROOT


@pytest.fixture(scope="session", autouse=True)
def clean_up_files():
    """
    Fixture that removes the media root folder after the suite has finished running,
    effectively deleting any files that were created by factories over the course of the test suite.
    """
    yield
    shutil.rmtree(TEST_MEDIA_ROOT)
