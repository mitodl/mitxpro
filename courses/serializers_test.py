"""
Tests for course serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
import pytest

from courses.factories import ProgramFactory, CourseFactory, CourseRunFactory
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from mitxpro.test_utils import drf_datetime


@pytest.mark.django_db
def test_serialize_program():
    """Test Program serialization"""
    program = ProgramFactory.create()
    data = ProgramSerializer(program).data
    assert data == {
        "title": program.title,
        "description": program.description,
        "readable_id": program.readable_id,
        "thumbnail": program.thumbnail,
        "live": program.live,
        "id": program.id,
        "created_on": drf_datetime(program.created_on),
        "updated_on": drf_datetime(program.updated_on),
    }


def test_deserialize_program():
    """Test Program deserialization"""
    data = {
        "title": "Some Title",
        "description": "Some Description",
        "readable_id": "some-id",
        "live": True,
    }
    serializer = ProgramSerializer(data=data)
    is_valid = serializer.is_valid(raise_exception=True)
    assert is_valid is True


@pytest.mark.django_db
def test_serialize_course():
    """Test Course serialization"""
    course = CourseFactory.create(no_program=True)
    data = CourseSerializer(course).data
    assert data == {
        "title": course.title,
        "description": course.description,
        "readable_id": course.readable_id,
        "thumbnail": course.thumbnail,
        "live": course.live,
        "position_in_program": None,
        "program": None,
        "id": course.id,
        "created_on": drf_datetime(course.created_on),
        "updated_on": drf_datetime(course.updated_on),
    }


@pytest.mark.django_db
def test_deserialize_course():
    """Test Course deserialization"""
    program = ProgramFactory.create()
    data = {
        "program": program.id,
        "position_in_program": 1,
        "title": "Some Title",
        "description": "Some Description",
        "readable_id": "some-id",
        "live": True,
    }
    serializer = CourseSerializer(data=data)
    is_valid = serializer.is_valid(raise_exception=True)
    assert is_valid is True
    assert serializer.data["program"] == program.id


@pytest.mark.django_db
def test_serialize_course_run():
    """Test CourseRun serialization"""
    course_run = CourseRunFactory.create()
    data = CourseRunSerializer(course_run).data
    assert data == {
        "title": course_run.title,
        "live": course_run.live,
        "courseware_id": course_run.courseware_id,
        "courseware_url_path": course_run.courseware_url_path,
        "start_date": drf_datetime(course_run.start_date),
        "end_date": drf_datetime(course_run.end_date),
        "enrollment_start": drf_datetime(course_run.enrollment_start),
        "enrollment_end": drf_datetime(course_run.enrollment_end),
        "course": course_run.course.id,
        "id": course_run.id,
        "created_on": drf_datetime(course_run.created_on),
        "updated_on": drf_datetime(course_run.updated_on),
    }


@pytest.mark.django_db
def test_deserialize_course_run():
    """Test CourseRun deserialization"""
    course = CourseFactory.create()
    data = {
        "course": course.id,
        "title": "Some Title",
        "courseware_id": "12345",
        "courseware_url_path": "/url/path",
        "start_date": "2019-01-01T00:00:00.000000Z",
        "end_date": "2019-01-02T00:00:00.000000Z",
        "enrollment_start": None,
        "enrollment_end": None,
        "live": True,
    }
    serializer = CourseRunSerializer(data=data)
    is_valid = serializer.is_valid(raise_exception=True)
    assert is_valid is True
    assert serializer.data["course"] == course.id
