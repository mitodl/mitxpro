"""Tests for course models"""
import pytest

from courses.factories import CourseFactory, CourseRunFactory


@pytest.mark.django_db
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
