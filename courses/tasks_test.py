"""Tests for Course related tasks"""

from collections import Counter
from datetime import timedelta

import pytest
from django.utils.timezone import now

from users.factories import UserFactory
from courses.factories import CourseRunFactory, PlatformFactory
from courses.sync_external_courses.external_course_sync_api import (
    EMERITUS_PLATFORM_NAME,
)
from courses.tasks import (
    sync_courseruns_data,
    task_sync_external_course_runs,
    generate_course_certificates,
)

pytestmark = [pytest.mark.django_db]


def test_sync_courseruns_data(mocker):
    """Test sync_courseruns_data calls the right api functionality from courses"""
    sync_course_runs = mocker.patch("courses.tasks.sync_course_runs")

    course_runs = CourseRunFactory.create_batch(size=3)
    CourseRunFactory.create_batch(size=3, course__is_external=True)

    sync_courseruns_data.delay()
    sync_course_runs.assert_called_once()

    called_args, _ = sync_course_runs.call_args
    actual_course_runs = called_args[0]
    assert Counter(actual_course_runs) == Counter(course_runs)


def test_task_sync_external_course_runs(mocker, settings):
    """Test task_sync_external_course_runs to call APIs for supported platforms and skip unsupported ones in EXTERNAL_COURSE_VENDOR_KEYMAPS"""
    mock_fetch_external_courses = mocker.patch("courses.tasks.fetch_external_courses")
    mock_update_external_course_runs = mocker.patch(
        "courses.tasks.update_external_course_runs"
    )
    mock_log = mocker.patch("courses.tasks.log")

    PlatformFactory.create(name=EMERITUS_PLATFORM_NAME, enable_sync=True)
    PlatformFactory.create(name="UnknownPlatform", enable_sync=True)

    task_sync_external_course_runs.delay()

    mock_fetch_external_courses.assert_called_once()
    mock_update_external_course_runs.assert_called_once()

    mock_log.exception.assert_called_once_with(
        "The platform '%s' does not have a sync API configured. Please disable the 'enable_sync' setting for this platform.",
        "UnknownPlatform",
    )


def test_task_generate_course_certificates(mocker):
    """Test generate_course_certificates calls the right API functionality making sure external courses are filtered out."""

    class MockEdxGrade:
        def __init__(self):
            self.percent = 0.85
            self.passed = True
            self.letter_grade = "B"

    user1 = UserFactory()
    user2 = UserFactory()

    mock_grades = [(MockEdxGrade(), user1), (MockEdxGrade(), user2)]

    mock_get_edx_grades = mocker.patch(
        "courses.tasks.get_edx_grades_with_users", return_value=mock_grades
    )
    mock_course_run_grade = mocker.Mock(name="course_run_grade")
    mock_ensure_grades = mocker.patch(
        "courses.tasks.ensure_course_run_grade",
        return_value=(mock_course_run_grade, True, False),
    )
    mock_process_grades = mocker.patch(
        "courses.tasks.process_course_run_grade_certificate",
        return_value=(mocker.Mock(), True, False),
    )

    mocker.patch("courses.tasks.exception_logging_generator", side_effect=lambda x: x)
    course_runs = CourseRunFactory.create_batch(
        size=3, end_date=now() - timedelta(days=2), force_insert=True
    )

    generate_course_certificates.delay()

    mock_get_edx_grades.assert_called()
    mock_ensure_grades.assert_called()
    mock_process_grades.assert_called()

    assert mock_get_edx_grades.call_count == len(course_runs)
    for run in course_runs:
        mock_get_edx_grades.assert_any_call(run)
