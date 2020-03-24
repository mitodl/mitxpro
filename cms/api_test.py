"""Tests for CMS API"""
from datetime import timedelta

import factory
import pytest
from cms.factories import (
    CoursePageFactory,
    ExternalCoursePageFactory,
    ProgramPageFactory,
)
from cms.models import ExternalCoursePage
from cms.api import filter_and_sort_catalog_pages
from courses.factories import CourseRunFactory
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db


def test_filter_and_sort_catalog_pages():  # pylint:disable=too-many-locals
    """
    Test that filter_and_sort_catalog_pages removes program/course/external course pages that do not have a future start date
    or enrollment end date, and returns appropriately sorted lists of pages
    """
    now = now_in_utc()

    earlier_external_course_page = ExternalCoursePageFactory.create(start_date=now)
    non_program_run = CourseRunFactory.create(
        course__no_program=True, start_date=(now + timedelta(days=1))
    )
    first_program_run = CourseRunFactory.create(start_date=(now + timedelta(days=2)))
    second_program_run = CourseRunFactory.create(start_date=(now + timedelta(days=3)))
    later_external_course_page = ExternalCoursePageFactory.create(
        start_date=now + timedelta(days=4)
    )
    # Create course run with past start_date and future enrollment_end, which should appear in the catalog
    future_enrollment_end_run = CourseRunFactory.create(
        past_start=True,
        enrollment_end=(now + timedelta(days=1)),
        course__no_program=True,
    )
    # Create course run with past start_date and enrollment_end, which should NOT appear in the catalog
    past_run = CourseRunFactory.create(
        past_start=True, past_enrollment_end=True, course__no_program=True
    )
    all_runs = [
        past_run,
        future_enrollment_end_run,
        second_program_run,
        first_program_run,
        non_program_run,
    ]

    external_course_pages = [earlier_external_course_page, later_external_course_page]

    initial_course_pages = CoursePageFactory.create_batch(
        len(all_runs), course=factory.Iterator(run.course for run in all_runs)
    )
    initial_program_pages = ProgramPageFactory.create_batch(
        2,
        program=factory.Iterator(
            run.course.program for run in [second_program_run, first_program_run]
        ),
    )

    all_pages, program_pages, course_pages = filter_and_sort_catalog_pages(
        initial_program_pages, initial_course_pages, external_course_pages
    )

    # Combined pages and course pages should not include the past course run
    assert len(all_pages) == (
        len(initial_program_pages)
        + len(initial_course_pages)
        + len(external_course_pages)
        - 1
    )
    assert len(course_pages) == (
        len(initial_course_pages) + len(external_course_pages) - 1
    )

    # Filtered out external course page because it does not have a `course` attribute
    assert past_run.course not in (
        None if page.is_external_course_page else page.course for page in course_pages
    )

    # Pages should be sorted by next run date
    assert [page.program for page in program_pages] == [
        first_program_run.course.program,
        second_program_run.course.program,
    ]
    expected_course_run_sort = [
        future_enrollment_end_run,
        earlier_external_course_page,
        non_program_run,
        first_program_run,
        second_program_run,
        later_external_course_page,
    ]

    # The sort should also include external course pages as expected
    assert [
        page if page.is_external_course_page else page.course for page in course_pages
    ] == [
        run if isinstance(run, ExternalCoursePage) else run.course
        for run in expected_course_run_sort
    ]
