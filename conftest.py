"""Project conftest"""
# pylint: disable=wildcard-import,unused-wildcard-import
import os
import shutil

import pytest
from django.conf import settings

from fixtures.autouse import *  # noqa: F403
from fixtures.common import *  # noqa: F403
from fixtures.cybersource import *  # noqa: F403

TEST_MEDIA_SUBDIR = "test_media_root"


def pytest_addoption(parser):
    """Pytest hook that adds command line parameters"""
    parser.addoption(
        "--simple",
        action="store_true",
        help="Run tests only (no cov, no pylint, warning output silenced)",
    )


def pytest_cmdline_main(config):
    """Pytest hook that runs after command line options are parsed"""
    if config.option.simple is True:
        config.option.pylint = False
        config.option.no_pylint = True


def pytest_configure(config):
    """Pytest hook to perform some initial configuration"""
    if not settings.MEDIA_ROOT.endswith(TEST_MEDIA_SUBDIR):
        settings.MEDIA_ROOT = os.path.join(  # noqa: PTH118
            settings.MEDIA_ROOT, TEST_MEDIA_SUBDIR
        )  # noqa: PTH118, RUF100

    if config.option.simple is True:
        # NOTE: These plugins are already configured by the time the pytest_cmdline_main hook is run, so we can't  # noqa: E501
        #       simply add/alter the command line options in that hook. This hook is being used to  # noqa: E501
        #       reconfigure/unregister plugins that we can't change via the pytest_cmdline_main hook.  # noqa: E501
        # Switch off coverage plugin
        cov = config.pluginmanager.get_plugin("_cov")
        cov.options.no_cov = True
        # Remove warnings plugin to suppress warnings
        if config.pluginmanager.has_plugin("warnings"):
            warnings_plugin = config.pluginmanager.get_plugin("warnings")
            config.pluginmanager.unregister(warnings_plugin)


@pytest.fixture(scope="session", autouse=True)
def clean_up_files():  # noqa: PT004
    """
    Fixture that removes the media root folder after the suite has finished running,
    effectively deleting any files that were created by factories over the course of the test suite.
    """  # noqa: E501
    yield
    if os.path.exists(settings.MEDIA_ROOT):  # noqa: PTH110
        shutil.rmtree(settings.MEDIA_ROOT)
