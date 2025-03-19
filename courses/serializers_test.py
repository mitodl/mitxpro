"""
Tests for course serializers
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import factory
import pytest
from django.contrib.auth.models import AnonymousUser

from cms.constants import FORMAT_HYBRID, FORMAT_ONLINE, FORMAT_OTHER
from cms.factories import FacultyMembersPageFactory
from courses.factories import (
    CourseFactory,
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramEnrollmentFactory,
    ProgramFactory,
)
from courses.models import CourseRun, CourseTopic
from courses.serializers import (
    BaseCourseSerializer,
    BaseProgramSerializer,
    CourseRunDetailSerializer,
    CourseRunEnrollmentSerializer,
    CourseRunSerializer,
    CourseSerializer,
    ProgramEnrollmentSerializer,
    ProgramSerializer,
)
from ecommerce.factories import ProductVersionFactory
from ecommerce.models import Order
from ecommerce.serializers import CompanySerializer
from ecommerce.serializers_test import datetime_millis_format
from mitxpro.test_utils import assert_drf_json_equal, drf_datetime

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
@pytest.mark.parametrize("is_external", [True, False])
@pytest.mark.parametrize("program_format", [FORMAT_ONLINE, FORMAT_HYBRID, FORMAT_OTHER])
@pytest.mark.parametrize(
    "duration, min_weeks, max_weeks, time_commitment, min_weekly_hours, max_weekly_hours, video_url, ceus, external_marketing_url, marketing_hubspot_form_id",  # noqa: PT006
    [
        (
            "2 weeks",
            4,
            4,
            "2 Hours",
            2,
            4,
            "http://www.testvideourl.com",
            "2.0",
            "https://www.testexternalcourse1.com",
            "fb4f5b79-test-4972-92c3-test",
        ),
        (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "",
        ),
    ],
)
def test_serialize_program(  # noqa: PLR0913
    mock_context,
    has_product,
    is_external,
    program_format,
    duration,
    min_weeks,
    max_weeks,
    time_commitment,
    min_weekly_hours,
    max_weekly_hours,
    video_url,
    ceus,
    external_marketing_url,
    marketing_hubspot_form_id,
):
    """Test Program serialization"""

    program = ProgramFactory.create(
        is_external=is_external,
        page__certificate_page__CEUs=ceus,
        page__duration=duration,
        page__min_weeks=min_weeks,
        page__max_weeks=max_weeks,
        page__format=program_format,
        page__time_commitment=time_commitment,
        page__min_weekly_hours=min_weekly_hours,
        page__max_weekly_hours=max_weekly_hours,
        page__video_url=video_url,
        page__external_marketing_url=external_marketing_url,
        page__marketing_hubspot_form_id=marketing_hubspot_form_id,
    )
    course1 = CourseFactory.create(program=program, position_in_program=1)
    course2 = CourseFactory.create(program=program, position_in_program=2)

    course1_runs = CourseRunFactory.create_batch(3, course=course1)
    course2_runs = CourseRunFactory.create_batch(3, course=course2)

    non_live_run = CourseRunFactory.create(
        course=course1,
        end_date=datetime.max.replace(tzinfo=UTC),
        expiration_date=None,
        live=False,
    )
    runs = course1_runs + course2_runs

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
    course1.page.topics.set([topics[0], topics[1]])
    course2.page.topics.set([topics[1], topics[2]])
    course1.page.save()
    course2.page.save()

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
            "start_date": program.first_unexpired_run.start_date,
            "end_date": sorted(runs, key=lambda run: run.end_date)[
                -1
            ].end_date.strftime(datetime_millis_format),
            "enrollment_start": program.first_unexpired_run.enrollment_start,
            "url": f"http://localhost{program.page.get_url()}",
            "instructors": [{"name": name} for name in faculty_names],
            "topics": [{"name": topic.name} for topic in topics],
            "time_commitment": time_commitment,
            "min_weekly_hours": min_weekly_hours,
            "max_weekly_hours": max_weekly_hours,
            "duration": duration,
            "max_weeks": max_weeks,
            "min_weeks": min_weeks,
            "format": program_format,
            "video_url": video_url,
            "credits": Decimal(ceus) if ceus else None,
            "is_external": is_external,
            "external_marketing_url": external_marketing_url,
            "marketing_hubspot_form_id": marketing_hubspot_form_id,
            "platform": program.platform.name,
            "availability": "dated",
            "prerequisites": [],
            "language": program.page.language.name if program.page else None,
        },
    )
    assert data["end_date"] != non_live_run.end_date.strftime(datetime_millis_format)


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
@pytest.mark.parametrize("is_external", [True, False])
@pytest.mark.parametrize("course_page", [True, False])
@pytest.mark.parametrize("course_format", [FORMAT_ONLINE, FORMAT_HYBRID, FORMAT_OTHER])
@pytest.mark.parametrize(
    "duration, min_weeks, max_weeks, time_commitment, min_weekly_hours, max_weekly_hours, video_url, ceus, external_marketing_url, marketing_hubspot_form_id",  # noqa: PT006
    [
        (
            "2 weeks",
            2,
            2,
            "2 Hours",
            2,
            4,
            "http://www.testvideourl.com",
            "2",
            "http://www.testexternalmarketingurl.com",
            "fb4f5b79-test-4972-92c3-test",
        ),
        (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "",
        ),
    ],
)
def test_serialize_course(  # noqa: PLR0913
    mock_context,
    is_anonymous,
    all_runs,
    is_external,
    course_page,
    course_format,
    duration,
    min_weeks,
    max_weeks,
    time_commitment,
    min_weekly_hours,
    max_weekly_hours,
    video_url,
    ceus,
    external_marketing_url,
    marketing_hubspot_form_id,
):
    """Test Course serialization"""
    now = datetime.now(tz=UTC)
    if is_anonymous:
        mock_context["request"].user = AnonymousUser()
    if all_runs:
        mock_context["all_runs"] = True
    user = mock_context["request"].user

    # Only create course page if required
    if course_page:
        course = CourseFactory.create(
            is_external=is_external,
            page__time_commitment=time_commitment,
            page__min_weekly_hours=min_weekly_hours,
            page__max_weekly_hours=max_weekly_hours,
            page__duration=duration,
            page__min_weeks=min_weeks,
            page__max_weeks=max_weeks,
            page__format=course_format,
            page__video_url=video_url,
            page__certificate_page__CEUs=ceus,
            page__external_marketing_url=external_marketing_url,
            page__marketing_hubspot_form_id=marketing_hubspot_form_id,
        )
    else:
        course = CourseFactory.create(page=None, is_external=is_external)

    course_run = CourseRunFactory.create(
        course=course,
        course__no_program=True,
        live=True,
    )
    topic = "a course topic"
    if course_page:
        course.page.topics.set([CourseTopic.objects.create(name=topic)])

    # Create expired, enrollment_ended, future, and enrolled course runs
    CourseRunFactory.create(
        course=course, end_date=now - timedelta(1), live=True, force_insert=True
    )
    CourseRunFactory.create(
        course=course, enrollment_end=now - timedelta(1), live=True, force_insert=True
    )
    CourseRunFactory.create(
        course=course,
        enrollment_start=now + timedelta(1),
        live=True,
        force_insert=True,
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
    expected_runs = unexpired_runs if all_runs or is_anonymous else [course_run]

    assert_drf_json_equal(
        data,
        {
            "title": course.title,
            "description": course.page.description if course_page else None,
            "url": f"http://localhost{course.page.get_url()}" if course_page else None,
            "readable_id": course.readable_id,
            "id": course.id,
            "courseruns": [
                CourseRunSerializer(run).data
                for run in sorted(expected_runs, key=lambda run: run.start_date)
            ],
            "thumbnail_url": f"http://localhost:8053{course.page.thumbnail_image.file.url if course_page else '/static/images/mit-dome.png'}",
            "next_run_id": course.first_unexpired_run.id,
            "topics": [{"name": topic}] if course_page else [],
            "time_commitment": time_commitment if course_page else None,
            "min_weekly_hours": min_weekly_hours if course_page else None,
            "max_weekly_hours": max_weekly_hours if course_page else None,
            "duration": duration if course_page else None,
            "max_weeks": max_weeks if course_page else None,
            "min_weeks": min_weeks if course_page else None,
            "format": course_format if course_page else None,
            "video_url": video_url if course_page else None,
            "credits": Decimal(ceus) if course_page and ceus else None,
            "is_external": is_external,
            "external_marketing_url": external_marketing_url if course_page else None,
            "marketing_hubspot_form_id": (
                marketing_hubspot_form_id if course_page else None
            ),
            "platform": course.platform.name,
            "availability": "dated",
            "prerequisites": [],
            "language": course.page.language.name if course.page else None,
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
    "has_company",
    [True, False],
)
def test_serialize_course_run_enrollments(settings, has_company):
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
        "certificate": None,
        "receipt": (
            course_run_enrollment.order_id
            if course_run_enrollment.order.status == Order.FULFILLED
            else None
        ),
    }


def test_serialize_program_enrollments_assert():
    """Test that ProgramEnrollmentSerializer throws an error when course run enrollments aren't provided"""
    program_enrollment = ProgramEnrollmentFactory.build()
    with pytest.raises(AssertionError):
        ProgramEnrollmentSerializer(program_enrollment)


@pytest.mark.parametrize(
    "has_company",
    [True, False],
)
def test_serialize_program_enrollments(settings, has_company):
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
        "certificate": None,
        "receipt": (
            program_enrollment.order_id
            if program_enrollment.order.status == Order.FULFILLED
            else None
        ),
    }
