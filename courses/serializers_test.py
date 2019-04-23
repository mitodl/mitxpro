"""
Tests for course serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
import pytest

from cms.factories import CoursePageFactory, ProgramPageFactory
from courses.factories import CourseRunFactory
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from mitxpro.test_utils import drf_datetime


pytestmark = [pytest.mark.django_db]


def test_serialize_program():
    """Test Program serialization"""
    run = CourseRunFactory.create()
    program = run.course.program
    page = ProgramPageFactory.create(program=program)
    data = ProgramSerializer(program).data
    assert data == {
        "title": program.title,
        "readable_id": program.readable_id,
        "id": program.id,
        "description": program.description,
        "courses": [CourseSerializer(run.course).data],
        "thumbnail_url": page.thumbnail_image.file.url,
    }


def test_serialize_course():
    """Test Course serialization"""
    run = CourseRunFactory.create(course__no_program=True)
    course = run.course
    page = CoursePageFactory.create(course=course)
    data = CourseSerializer(course).data
    assert data == {
        "title": course.title,
        "description": course.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "courseruns": [CourseRunSerializer(run).data],
        "thumbnail_url": page.thumbnail_image.file.url,
    }


def test_serialize_course_run():
    """Test CourseRun serialization"""
    course_run = CourseRunFactory.create()
    data = CourseRunSerializer(course_run).data
    assert data == {
        "title": course_run.title,
        "courseware_id": course_run.courseware_id,
        "courseware_url_path": course_run.courseware_url_path,
        "start_date": drf_datetime(course_run.start_date),
        "end_date": drf_datetime(course_run.end_date),
        "enrollment_start": drf_datetime(course_run.enrollment_start),
        "enrollment_end": drf_datetime(course_run.enrollment_end),
        "id": course_run.id,
    }
