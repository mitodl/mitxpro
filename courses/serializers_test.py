"""
Tests for course serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
from datetime import datetime, timedelta

import factory
from django.contrib.auth.models import AnonymousUser
import pytest
import pytz

from cms.factories import FacultyMembersPageFactory
from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    ProgramFactory,
    CourseRunEnrollmentFactory,
    ProgramEnrollmentFactory,
)
from courses.models import CourseTopic, CourseRun
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
from ecommerce.factories import ProductVersionFactory
from ecommerce.models import Order
from ecommerce.serializers import CompanySerializer
from ecommerce.serializers_test import datetime_format
from mitxpro.test_utils import drf_datetime, assert_drf_json_equal

pytestmark = [pytest.mark.django_db]


def test_base_program_serializer():
    """Test BaseProgramSerializer serialization"""
    program = ProgramFactory.create()
    data = BaseProgramSerializer(program).data
    assert data == {
        "title": program.title,
        "readable_id": program.readable_id,
        "id": program.id,
        "description": program.page.description,
        "thumbnail_url": f"http://localhost:8053{program.page.thumbnail_image.file.url}",
    }


@pytest.mark.parametrize("has_product", [True, False])
def test_serialize_program(mock_context, has_product):
    """Test Program serialization"""
    program = ProgramFactory.create()
    run1 = CourseRunFactory.create(course__program=program)
    course1 = run1.course
    run2 = CourseRunFactory.create(course__program=program)
    course2 = run2.course
    runs = (
        [run1, run2]
        + [CourseRunFactory.create(course=course1) for _ in range(2)]
        + [CourseRunFactory.create(course=course2) for _ in range(2)]
    )
    faculty_names = ["Teacher 1", "Teacher 2"]
    FacultyMembersPageFactory.create(
        parent=program.page,
        **{
            f"members__{idx}__member__name": name
            for idx, name in enumerate(faculty_names)
        },
    )
    if has_product:
        ProductVersionFactory.create(product__content_object=program)
    topics = [CourseTopic.objects.create(name=f"topic{num}") for num in range(3)]
    course1.topics.set([topics[0], topics[1]])
    course2.topics.set([topics[1], topics[2]])

    data = ProgramSerializer(instance=program, context=mock_context).data

    assert_drf_json_equal(
        data,
        {
            "title": program.title,
            "readable_id": program.readable_id,
            "id": program.id,
            "description": program.page.description,
            "courses": [
                CourseSerializer(
                    instance=course, context={**mock_context, "filter_products": False}
                ).data
                for course in [course1, course2]
            ],
            "thumbnail_url": f"http://localhost:8053{program.page.thumbnail_image.file.url}",
            "current_price": program.current_price,
            "start_date": sorted(runs, key=lambda run: run.start_date)[
                0
            ].start_date.strftime(datetime_format),
            "end_date": sorted(runs, key=lambda run: run.end_date)[
                -1
            ].end_date.strftime(datetime_format),
            "enrollment_start": sorted(runs, key=lambda run: run.enrollment_start)[
                0
            ].enrollment_start.strftime(datetime_format),
            "url": f"http://localhost{program.page.get_url()}",
            "instructors": [{"name": name} for name in faculty_names],
            "topics": [{"name": topic.name} for topic in topics],
        },
    )


def test_base_course_serializer():
    """Test CourseRun serialization"""
    course = CourseFactory.create()
    data = BaseCourseSerializer(course).data
    assert data == {
        "title": course.title,
        "description": course.page.description,
        "readable_id": course.readable_id,
        "id": course.id,
        "thumbnail_url": f"http://localhost:8053{course.page.thumbnail_image.file.url}",
    }


@pytest.mark.parametrize("is_anonymous", [True, False])
@pytest.mark.parametrize("all_runs", [True, False])
def test_serialize_course(mock_context, is_anonymous, all_runs):
    """Test Course serialization"""
    now = datetime.now(tz=pytz.UTC)
    if is_anonymous:
        mock_context["request"].user = AnonymousUser()
    if all_runs:
        mock_context["all_runs"] = True
    user = mock_context["request"].user
    course_run = CourseRunFactory.create(course__no_program=True, live=True)
    course = course_run.course
    topic = "a course topic"
    course.topics.set([CourseTopic.objects.create(name=topic)])

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

    # create products for all courses so the serializer shows them
    for run in CourseRun.objects.all():
        ProductVersionFactory.create(product__content_object=run)

    data = CourseSerializer(instance=course, context=mock_context).data

    if all_runs or is_anonymous:
        expected_runs = unexpired_runs
    else:
        expected_runs = [course_run]

    assert_drf_json_equal(
        data,
        {
            "title": course.title,
            "description": course.page.description,
            "readable_id": course.readable_id,
            "id": course.id,
            "courseruns": [
                CourseRunSerializer(run).data
                for run in sorted(expected_runs, key=lambda run: run.start_date)
            ],
            "thumbnail_url": f"http://localhost:8053{course.page.thumbnail_image.file.url}",
            "next_run_id": course.first_unexpired_run.id,
            "topics": [{"name": topic}],
        },
    )


@pytest.mark.parametrize("has_product", [True, False])
def test_serialize_course_run(has_product):
    """Test CourseRun serialization"""
    faculty_names = ["Emma Jones", "Joe Smith"]
    course_run = CourseRunFactory.create()
    FacultyMembersPageFactory.create(
        parent=course_run.course.page,
        **{
            f"members__{idx}__member__name": name
            for idx, name in enumerate(faculty_names)
        },
    )
    product_id = (
        ProductVersionFactory.create(product__content_object=course_run).product.id
        if has_product
        else None
    )

    course_run.refresh_from_db()

    data = CourseRunSerializer(course_run).data
    assert_drf_json_equal(
        data,
        {
            "title": course_run.title,
            "courseware_id": course_run.courseware_id,
            "run_tag": course_run.run_tag,
            "courseware_url": course_run.courseware_url,
            "start_date": drf_datetime(course_run.start_date),
            "end_date": drf_datetime(course_run.end_date),
            "enrollment_start": drf_datetime(course_run.enrollment_start),
            "enrollment_end": drf_datetime(course_run.enrollment_end),
            "expiration_date": drf_datetime(course_run.expiration_date),
            "current_price": course_run.current_price,
            "instructors": course_run.instructors,
            "id": course_run.id,
            "product_id": product_id,
        },
    )


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


@pytest.mark.parametrize(
    "has_company, receipts_enabled",
    [[True, False], [False, False], [False, True], [True, True]],
)
def test_serialize_course_run_enrollments(settings, has_company, receipts_enabled):
    """Test that CourseRunEnrollmentSerializer has correct data"""
    settings.ENABLE_ORDER_RECEIPTS = receipts_enabled
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
        "certificate": None,
        "receipt": course_run_enrollment.order_id
        if course_run_enrollment.order.status == Order.FULFILLED and receipts_enabled
        else None,
    }


def test_serialize_program_enrollments_assert():
    """Test that ProgramEnrollmentSerializer throws an error when course run enrollments aren't provided"""
    program_enrollment = ProgramEnrollmentFactory.build()
    with pytest.raises(AssertionError):
        ProgramEnrollmentSerializer(program_enrollment)


@pytest.mark.parametrize(
    "has_company, receipts_enabled",
    [[True, False], [False, False], [False, True], [True, True]],
)
def test_serialize_program_enrollments(settings, has_company, receipts_enabled):
    """Test that ProgramEnrollmentSerializer has correct data"""
    settings.ENABLE_ORDER_RECEIPTS = receipts_enabled
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
        "certificate": None,
        "receipt": program_enrollment.order_id
        if program_enrollment.order.status == Order.FULFILLED and receipts_enabled
        else None,
    }
