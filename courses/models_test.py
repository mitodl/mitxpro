"""Tests for course models"""
from datetime import timedelta

import pytest

from courses.factories import CourseFactory, CourseRunFactory
from mitxpro.utils import now_in_utc

pytestmark = [pytest.mark.django_db]


def test_program_course_auto_position():
    """
    If a course is added to a program with no position specified, it should be given the last position
    """
    first_course = CourseFactory.create(position_in_program=None)
    assert first_course.position_in_program == 1
    second_course = CourseFactory.create(
        program=first_course.program, position_in_program=None
    )
    assert second_course.position_in_program == 2


def test_courseware_url(settings):
    """Test that the courseware_url property yields the correct values"""
    settings.OPENEDX_BASE_REDIRECT_URL = "http://example.com"
    course_run = CourseRunFactory.build(courseware_url_path="/path")
    course_run_no_path = CourseRunFactory.build(courseware_url_path=None)
    assert course_run.courseware_url == "http://example.com/path"
    assert course_run_no_path.courseware_url is None


@pytest.mark.parametrize("expected", [True, False])
def test_course_run_past(expected):
    """
    Test that CourseRun.is_past returns the expected boolean value
    """
    now = now_in_utc()
    if expected is True:
        end_date = now - timedelta(days=1)
    else:
        end_date = now + timedelta(days=1)
    assert CourseRunFactory.create(end_date=end_date).is_past is expected


@pytest.mark.parametrize(
    "end_days, enroll_days, expected",
    [
        [None, None, True],
        [None, 1, True],
        [None, -1, False],
        [1, None, True],
        [-1, None, False],
        [1, -1, False],
    ],
)
def test_course_run_not_beyond_enrollment(end_days, enroll_days, expected):
    """
    Test that CourseRun.is_beyond_enrollment returns the expected boolean value
    """
    now = now_in_utc()
    end_date = None if end_days is None else now + timedelta(days=end_days)
    enr_end_date = None if enroll_days is None else now + timedelta(days=enroll_days)
    assert (
        CourseRunFactory.create(
            end_date=end_date, enrollment_end=enr_end_date
        ).is_not_beyond_enrollment
        is expected
    )


@pytest.mark.parametrize(
    "end_days,enroll_days,expected", [[-1, 1, False], [1, -1, False], [1, 1, True]]
)
def test_course_run_unexpired(end_days, enroll_days, expected):
    """
    Test that CourseRun.is_unexpired returns the expected boolean value
    """
    now = now_in_utc()
    end_date = now + timedelta(days=end_days)
    enr_end_date = now + timedelta(days=enroll_days)
    assert (
        CourseRunFactory.create(
            end_date=end_date, enrollment_end=enr_end_date
        ).is_unexpired
        is expected
    )


def test_course_first_unexpired_run():
    """
    Test that the first unexpired run of a course is returned
    """
    course = CourseFactory.create()
    now = now_in_utc()
    end_date = now + timedelta(days=100)
    enr_end_date = now + timedelta(days=100)
    first_run = CourseRunFactory.create(
        start_date=now, course=course, end_date=end_date, enrollment_end=enr_end_date
    )
    CourseRunFactory.create(
        start_date=now + timedelta(days=50),
        course=course,
        end_date=end_date,
        enrollment_end=enr_end_date,
    )
    assert course.first_unexpired_run == first_run
