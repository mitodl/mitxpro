"""Tests for Course related tasks"""

import pytest

from courses.tasks import generate_course_certificates, sync_courseruns_data

pytestmark = pytest.mark.django_db


def test_generate_course_certificates_task(mocker):
    """Test generate_course_certificates calls the right api functionality from courses"""
    generate_course_run_certificates = mocker.patch(
        "courses.api.generate_course_run_certificates"
    )
    generate_course_certificates.delay()
    generate_course_run_certificates.assert_called_once()


def test_sync_courseruns_data(mocker):
    """Test sync_courseruns_data calls the right api functionality from courses"""
    sync_course_runs_data_task = mocker.patch("courses.api.sync_course_runs_data")
    sync_courseruns_data.delay()
    sync_course_runs_data_task.assert_called_once()
