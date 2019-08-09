"""
Tests for course serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
from datetime import datetime, timedelta

import factory
from django.contrib.auth.models import AnonymousUser
import pytest
import pytz

from cms.factories import (
    CoursePageFactory,
    ProgramPageFactory,
    FacultyMembersPageFactory,
)
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
from ecommerce.serializers import CompanySerializer
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
        "description": page.description,
        "thumbnail_url": page.thumbnail_image.file.url,
    }


def test_serialize_program(mock_context):
    """Test Program serialization"""
    run = CourseRunFactory.create()
    program = run.course.program
    page = ProgramPageFactory.create(program=program)
    data = ProgramSerializer(instance=program, context=mock_context).data
    assert data == {
        "title": program.title,
        "readable_id": program.readable_id,
        "id": program.id,
        "description": page.description,
        "courses": [CourseSerializer(instance=run.course, context=mock_context).data],
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
        "description": page.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "thumbnail_url": page.thumbnail_image.file.url,
    }


@pytest.mark.parametrize("is_anonymous", [True, False])
@pytest.mark.parametrize("all_runs", [True, False])
def test_serialize_course(mock_context, is_anonymous, all_runs):
    """Test Course serialization"""
    now = datetime.now(tz=pytz.UTC)
    if is_anonymous:
        mock_context["request"].user = AnonymousUser()
    user = mock_context["request"].user
    if all_runs:
        mock_context["all_runs"] = True
    course_run = CourseRunFactory.create(course__no_program=True, live=True)
    course = course_run.course

    # Create expired, enrollment_ended, future, and enrolled course runs
    CourseRunFactory.create(course=course, end_date=now - timedelta(1), live=True)
    CourseRunFactory.create(course=course, enrollment_end=now - timedelta(1), live=True)
    CourseRunFactory.create(
        course=course, enrollment_start=now + timedelta(1), live=True
    )
    enrolled_run = CourseRunFactory.create(course=course, live=True)
    unexpired_runs = [enrolled_run, course_run]
    CourseRunEnrollmentFactory.create(
        run=enrolled_run, **({} if is_anonymous else {"user": user})
    )

    page = CoursePageFactory.create(course=course)
    data = CourseSerializer(instance=course, context=mock_context).data

    if all_runs:
        expected_runs = unexpired_runs
    elif not is_anonymous:
        expected_runs = [course_run]
    else:
        expected_runs = []

    assert data == {
        "title": course.title,
        "description": page.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "courseruns": [
            CourseRunSerializer(run).data
            for run in sorted(expected_runs, key=lambda run: run.start_date)
        ],
        "thumbnail_url": page.thumbnail_image.file.url,
        "next_run_id": course.first_unexpired_run.id,
    }


def test_serialize_course_run():
    """Test CourseRun serialization"""
    faculty_names = ["Emma Jones", "Joe Smith"]
    course_run = CourseRunFactory.create()
    course_page = CoursePageFactory.create(course=course_run.course)
    FacultyMembersPageFactory.create(
        parent=course_page,
        **{
            f"members__{idx}__member__name": name
            for idx, name in enumerate(faculty_names)
        },
    )
    course_run.refresh_from_db()
    # instructors =
    data = CourseRunSerializer(course_run).data
    assert data == {
        "title": course_run.title,
        "courseware_id": course_run.courseware_id,
        "courseware_url": course_run.courseware_url,
        "start_date": drf_datetime(course_run.start_date),
        "end_date": drf_datetime(course_run.end_date),
        "enrollment_start": drf_datetime(course_run.enrollment_start),
        "enrollment_end": drf_datetime(course_run.enrollment_end),
        "expiration_date": drf_datetime(course_run.expiration_date),
        "instructors": [{"name": name} for name in faculty_names],
        "id": course_run.id,
        "product_id": None,
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
        "expiration_date": drf_datetime(course_run.expiration_date),
        "id": course_run.id,
    }


@pytest.mark.parametrize("has_company", [True, False])
def test_serialize_course_run_enrollments(has_company):
    """Test that CourseRunEnrollmentSerializer has correct data"""
    course_run_enrollment = CourseRunEnrollmentFactory.create(
        has_company_affiliation=has_company
    )
    serialized_data = CourseRunEnrollmentSerializer(course_run_enrollment).data
    assert serialized_data == {
        "run": CourseRunDetailSerializer(course_run_enrollment.run).data,
        "company": (
            CompanySerializer(course_run_enrollment.company).data
            if has_company
            else None
        ),
    }


def test_serialize_program_enrollments_assert():
    """Test that ProgramEnrollmentSerializer throws an error when course run enrollments aren't provided"""
    program_enrollment = ProgramEnrollmentFactory.build()
    with pytest.raises(AssertionError):
        ProgramEnrollmentSerializer(program_enrollment)


@pytest.mark.parametrize("has_company", [True, False])
def test_serialize_program_enrollments(has_company):
    """Test that ProgramEnrollmentSerializer has correct data"""
    program = ProgramFactory.create()
    course_run_enrollments = CourseRunEnrollmentFactory.create_batch(
        3,
        run__course__program=factory.Iterator([program, program, None]),
        run__course__position_in_program=factory.Iterator([2, 1, None]),
    )
    program_enrollment = ProgramEnrollmentFactory.create(
        program=program, has_company_affiliation=has_company
    )
    serialized_data = ProgramEnrollmentSerializer(
        program_enrollment, context={"course_run_enrollments": course_run_enrollments}
    ).data
    assert serialized_data == {
        "id": program_enrollment.id,
        "program": BaseProgramSerializer(program).data,
        "company": (
            CompanySerializer(program_enrollment.company).data if has_company else None
        ),
        # Only enrollments for the given program should be serialized, and they should be
        # sorted by position in program.
        "course_run_enrollments": CourseRunEnrollmentSerializer(
            [course_run_enrollments[1], course_run_enrollments[0]], many=True
        ).data,
    }
