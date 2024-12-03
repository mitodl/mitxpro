"""Tests for Course related tasks"""

from collections import Counter

import pytest

from courses.factories import CourseRunFactory
from courses.tasks import sync_courseruns_data, task_sync_emeritus_course_runs

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


def test_task_sync_emeritus_course_runs(mocker, settings):
    """Test task_sync_emeritus_course_runs calls the right api functionality"""
    settings.FEATURES["ENABLE_EXTERNAL_COURSE_SYNC"] = True
    mock_fetch_external_courses = mocker.patch("courses.tasks.fetch_external_courses")
    mock_update_external_course_runs = mocker.patch(
        "courses.tasks.update_external_course_runs"
    )
    task_sync_emeritus_course_runs.delay()
    mock_fetch_external_courses.assert_called_once()
    mock_update_external_course_runs.assert_called_once()
