"""
Tests for course serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
import factory
import pytest

from cms.factories import CoursePageFactory, ProgramPageFactory
from courses.factories import (
    CourseRunFactory,
    ProgramFactory,
    CourseRunEnrollmentFactory,
    ProgramEnrollmentFactory,
)
from courses.serializers import (
    ProgramSerializer,
    CourseSerializer,
    CourseRunSerializer,
    BaseProgramSerializer,
    BaseCourseSerializer,
    CourseRunDetailSerializer,
    CourseRunEnrollmentSerializer,
    ProgramEnrollmentSerializer,
)
from mitxpro.test_utils import drf_datetime


pytestmark = [pytest.mark.django_db]


def test_base_program_serializer():
    """Test BaseProgramSerializer serialization"""
    run = CourseRunFactory.create()
    program = run.course.program
    page = ProgramPageFactory.create(program=program)
    data = BaseProgramSerializer(program).data
    assert data == {
        "title": program.title,
        "readable_id": program.readable_id,
        "id": program.id,
        "description": program.description,
        "thumbnail_url": page.thumbnail_image.file.url,
    }


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


def test_base_course_serializer():
    """Test CourseRun serialization"""
    run = CourseRunFactory.create(course__no_program=True)
    course = run.course
    page = CoursePageFactory.create(course=course)
    data = BaseCourseSerializer(course).data
    assert data == {
        "title": course.title,
        "description": course.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "thumbnail_url": page.thumbnail_image.file.url,
    }


@pytest.mark.parametrize("with_runs", [True, False])
def test_serialize_course(with_runs):
    """Test Course serialization"""
    run = CourseRunFactory.create(course__no_program=True)
    course = run.course
    if not with_runs:
        course.courseruns.all().delete()
    page = CoursePageFactory.create(course=course)
    data = CourseSerializer(course).data
    assert data == {
        "title": course.title,
        "description": course.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "courseruns": [CourseRunSerializer(run).data] if with_runs else [],
        "thumbnail_url": page.thumbnail_image.file.url,
        "next_run_id": course.first_unexpired_run.id if with_runs else None,
    }


def test_serialize_course_run():
    """Test CourseRun serialization"""
    course_run = CourseRunFactory.create()
    data = CourseRunSerializer(course_run).data
    assert data == {
        "title": course_run.title,
        "courseware_id": course_run.courseware_id,
        "courseware_url": course_run.courseware_url,
        "start_date": drf_datetime(course_run.start_date),
        "end_date": drf_datetime(course_run.end_date),
        "enrollment_start": drf_datetime(course_run.enrollment_start),
        "enrollment_end": drf_datetime(course_run.enrollment_end),
        "id": course_run.id,
    }


def test_serialize_course_run_detail():
    """Test CourseRunDetailSerializer serialization"""
    course_run = CourseRunFactory.create()
    data = CourseRunDetailSerializer(course_run).data
    assert data == {
        "course": BaseCourseSerializer(course_run.course).data,
        "title": course_run.title,
        "courseware_id": course_run.courseware_id,
        "courseware_url": course_run.courseware_url,
        "start_date": drf_datetime(course_run.start_date),
        "end_date": drf_datetime(course_run.end_date),
        "enrollment_start": drf_datetime(course_run.enrollment_start),
        "enrollment_end": drf_datetime(course_run.enrollment_end),
        "id": course_run.id,
    }


def test_serialize_course_run_enrollments():
    """Test that CourseRunEnrollmentSerializer has correct data"""
    course_run_enrollment = CourseRunEnrollmentFactory.create()
    serialized_data = CourseRunEnrollmentSerializer(course_run_enrollment).data
    assert serialized_data == {
        "run": CourseRunDetailSerializer(course_run_enrollment.run).data
    }


def test_serialize_program_enrollments_assert():
    """Test that ProgramEnrollmentSerializer throws an error when course run enrollments aren't provided"""
    program_enrollment = ProgramEnrollmentFactory.build()
    with pytest.raises(AssertionError):
        ProgramEnrollmentSerializer(program_enrollment)


def test_serialize_program_enrollments():
    """Test that ProgramEnrollmentSerializer has correct data"""
    program = ProgramFactory.create()
    course_run_enrollments = CourseRunEnrollmentFactory.create_batch(
        3,
        run__course__program=factory.Iterator([program, program, None]),
        run__course__position_in_program=factory.Iterator([2, 1, None]),
    )
    program_enrollment = ProgramEnrollmentFactory.create(program=program)
    serialized_data = ProgramEnrollmentSerializer(
        program_enrollment, context={"course_run_enrollments": course_run_enrollments}
    ).data
    assert serialized_data == {
        "id": program_enrollment.id,
        "program": BaseProgramSerializer(program).data,
        # Only enrollments for the given program should be serialized, and they should be
        # sorted by position in program.
        "course_run_enrollments": CourseRunEnrollmentSerializer(
            [course_run_enrollments[1], course_run_enrollments[0]], many=True
        ).data,
    }
