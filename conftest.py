"""Project conftest"""

import os
import shutil

import pytest
from django.conf import settings
from wagtail.models import Page, Site

from cms.constants import (
    BLOG_INDEX_SLUG,
    CERTIFICATE_INDEX_SLUG,
    COURSE_INDEX_SLUG,
    PROGRAM_INDEX_SLUG,
    SIGNATORY_INDEX_SLUG,
    WEBINAR_INDEX_SLUG,
)
from cms.models import (
    BlogIndexPage,
    CertificateIndexPage,
    CourseIndexPage,
    ProgramIndexPage,
    SignatoryIndexPage,
    WebinarIndexPage,
)
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
    if getattr(config.option, "simple") is True:  # noqa: B009
        config.option.pylint = False
        config.option.no_pylint = True


def pytest_configure(config):
    """Pytest hook to perform some initial configuration"""
    if not settings.MEDIA_ROOT.endswith(TEST_MEDIA_SUBDIR):
        settings.MEDIA_ROOT = os.path.join(settings.MEDIA_ROOT, TEST_MEDIA_SUBDIR)  # noqa: PTH118

    if getattr(config.option, "simple") is True:  # noqa: B009
        # NOTE: These plugins are already configured by the time the pytest_cmdline_main hook is run, so we can't
        #       simply add/alter the command line options in that hook. This hook is being used to
        #       reconfigure/unregister plugins that we can't change via the pytest_cmdline_main hook.
        # Switch off coverage plugin
        cov = config.pluginmanager.get_plugin("_cov")
        cov.options.no_cov = True
        # Remove warnings plugin to suppress warnings
        if config.pluginmanager.has_plugin("warnings"):
            warnings_plugin = config.pluginmanager.get_plugin("warnings")
            config.pluginmanager.unregister(warnings_plugin)


@pytest.fixture(scope="session", autouse=True)
def clean_up_files():
    """
    Fixture that removes the media root folder after the suite has finished running,
    effectively deleting any files that were created by factories over the course of the test suite.
    """
    yield
    if os.path.exists(settings.MEDIA_ROOT):  # noqa: PTH110
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # noqa: ARG001
    """
    Creates all the index pages during the tests setup as index pages are required by the factories.
    """
    with django_db_blocker.unblock():
        site = Site.objects.filter(is_default_site=True).first()
        home_page = Page.objects.get(id=site.root_page.id)

        index_page_data_mapping = {
            ProgramIndexPage: {"title": "Programs", "slug": PROGRAM_INDEX_SLUG},
            CourseIndexPage: {"title": "Courses", "slug": COURSE_INDEX_SLUG},
            CertificateIndexPage: {
                "title": "Certificates",
                "slug": CERTIFICATE_INDEX_SLUG,
            },
            SignatoryIndexPage: {"title": "Signatories", "slug": SIGNATORY_INDEX_SLUG},
            BlogIndexPage: {"title": "Blogs", "slug": BLOG_INDEX_SLUG},
            WebinarIndexPage: {"title": "Webinars", "slug": WEBINAR_INDEX_SLUG},
        }
        for index_page_class, index_page_content in index_page_data_mapping.items():
            if not index_page_class.objects.filter(**index_page_content).exists():
                index_page = index_page_class(**index_page_content)
                home_page.add_child(instance=index_page)
