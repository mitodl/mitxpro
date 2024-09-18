"""Tests for CMS API"""

from datetime import timedelta

import pytest

from cms.api import filter_and_sort_catalog_pages
from cms.constants import CatalogSorting
from cms.factories import (
    ExternalCoursePageFactory,
    ExternalProgramPageFactory,
)
from courses.factories import (
    CourseRunFactory,
    ProgramFactory,
    ProgramRunFactory,
)
from ecommerce.factories import ProductFactory, ProductVersionFactory
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "sort_by",
    [
        CatalogSorting.BEST_MATCH.sorting_value,
        CatalogSorting.START_DATE_ASC.sorting_value,
    ],
)
def test_filter_and_sort_catalog_pages_with_default_sorting(sort_by):
    """
    Test that filter_and_sort_catalog_pages removes program/course/external course pages that do not have a future start date
    or enrollment end date, and returns appropriately sorted lists of pages
    """
    now = now_in_utc()

    earlier_external_course_page = ExternalCoursePageFactory.create()
    CourseRunFactory.create(course=earlier_external_course_page.course, start_date=now)
    earlier_external_program_page = ExternalProgramPageFactory.create()
    ProgramRunFactory.create(
        program=earlier_external_program_page.program, start_date=now
    )

    non_program_run = CourseRunFactory.create(
        course__no_program=True, start_date=(now + timedelta(days=1))
    )
    first_program_run = CourseRunFactory.create(start_date=(now + timedelta(days=2)))
    second_program_run = CourseRunFactory.create(start_date=(now + timedelta(days=3)))
    later_external_course_page = ExternalCoursePageFactory.create()
    CourseRunFactory.create(
        course=later_external_course_page.course, start_date=now + timedelta(days=4)
    )
    later_external_program_page = ExternalProgramPageFactory.create()
    # Create course run with past start_date and future enrollment_end, which should appear in the catalog
    CourseRunFactory.create(
        course__program=later_external_program_page.program,
        start_date=now + timedelta(days=4),
    )
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

    external_program_pages = [
        earlier_external_program_page,
        later_external_program_page,
    ]

    initial_course_pages = [run.course.page for run in all_runs]
    initial_program_pages = [
        run.course.program.page for run in [second_program_run, first_program_run]
    ]

    all_pages, program_pages, course_pages = filter_and_sort_catalog_pages(
        initial_program_pages,
        initial_course_pages,
        external_course_pages,
        external_program_pages,
        sort_by,
    )

    # Combined pages and course pages should not include the past course run
    assert len(all_pages) == (
        len(initial_program_pages)
        + len(initial_course_pages)
        + len(external_course_pages)
        + len(external_program_pages)
        - 2
    )
    assert len(course_pages) == (
        len(initial_course_pages) + len(external_course_pages) - 1
    )

    assert len(program_pages) == (
        len(initial_program_pages) + len(external_program_pages) - 1
    )

    # Filtered out external course page because it does not have a `course` attribute
    assert past_run.course not in (
        None if page.is_external_course_page else page.course for page in course_pages
    )

    # Pages should be sorted by next run date
    assert [page.program for page in program_pages] == [
        first_program_run.course.program,
        second_program_run.course.program,
        later_external_program_page.program,
    ]
    expected_course_run_sort = [
        non_program_run,
        first_program_run,
        second_program_run,
        later_external_course_page,
        future_enrollment_end_run,
        earlier_external_course_page,
    ]

    # The sort should also include external course pages as expected
    assert [page.course for page in course_pages] == [
        run.course for run in expected_course_run_sort
    ]


@pytest.mark.parametrize(
    (
        "sort_by",
        "course_prices",
        "program_prices",
        "expected_all_tab_prices",
        "expected_course_tab_prices",
        "expected_program_tab_prices",
    ),
    [
        (
            CatalogSorting.PRICE_ASC.sorting_value,
            [120, 10, None, 500, None, 1000],
            [220, 50, None, 5000, None, 21000],
            [10, 50, 120, 220, 500, 1000, 5000, 21000, None, None, None, None],
            [10, 120, 500, 1000, None, None],
            [50, 220, 5000, 21000, None, None],
        ),
        (
            CatalogSorting.PRICE_DESC.sorting_value,
            [120, 10, None, 500, None, 1000],
            [220, 50, None, 5000, None, 21000],
            [21000, 5000, 1000, 500, 220, 120, 50, 10, None, None, None, None],
            [1000, 500, 120, 10, None, None],
            [21000, 5000, 220, 50, None, None],
        ),
    ],
)
def test_filter_and_sort_catalog_pages_with_price_sorting(  # noqa: PLR0913
    sort_by,
    course_prices,
    program_prices,
    expected_all_tab_prices,
    expected_course_tab_prices,
    expected_program_tab_prices,
):
    """Tests that `filter_and_sort_catalog_pages` returns appropriately sorted lists of courseware pages"""
    now = now_in_utc()

    course_page_list = []
    for price in course_prices:
        run = CourseRunFactory.create(
            past_start=True,
            enrollment_end=(now + timedelta(days=1)),
            course__no_program=True,
        )

        if price is not None:
            ProductVersionFactory.create(
                product=ProductFactory.create(content_object=run), price=price
            )

        course_page_list.append(run.course.coursepage)

    program_page_list = []
    for price in program_prices:
        program = ProgramFactory.create()
        CourseRunFactory.create(
            course__program=program,
            past_start=True,
            enrollment_end=(now + timedelta(days=1)),
            course__no_program=True,
        )

        if price is not None:
            ProductVersionFactory.create(
                product=ProductFactory.create(content_object=program), price=price
            )

        program_page_list.append(program.programpage)

    all_pages, program_pages, course_pages = filter_and_sort_catalog_pages(
        program_page_list,
        course_page_list,
        [],
        [],
        sort_by,
    )

    assert len(all_pages) == len(course_page_list) + len(program_page_list)
    assert len(course_pages) == len(course_page_list)
    assert len(program_pages) == len(program_page_list)

    assert [page.product.current_price for page in all_pages] == expected_all_tab_prices
    assert [
        page.product.current_price for page in course_pages
    ] == expected_course_tab_prices
    assert [
        page.product.current_price for page in program_pages
    ] == expected_program_tab_prices
