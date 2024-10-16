from datetime import timedelta

import pytest

from cms.factories import (
    CoursePageFactory,
    ExternalCoursePageFactory,
    ExternalProgramPageFactory,
    ProgramPageFactory,
)
from courses.data_provider import CoursePageProvider, ProgramPageProvider
from courses.factories import CourseFactory, CourseRunFactory, ProgramFactory
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("is_external", [True, False])
@pytest.mark.parametrize("is_program_live", [True, False])
@pytest.mark.parametrize("has_program_page", [True, False])
@pytest.mark.parametrize("is_program_page_live", [True, False])
@pytest.mark.parametrize("has_course", [True, False])
@pytest.mark.parametrize("has_course_run", [True, False])
@pytest.mark.parametrize(
    "start_date",
    [None, now_in_utc() + timedelta(days=1), now_in_utc() - timedelta(days=1)],
)
@pytest.mark.parametrize(
    "enrollment_end_date",
    [None, now_in_utc() + timedelta(days=1), now_in_utc() - timedelta(days=1)],
)
def test_filter_program_pages(  # noqa: PLR0913
    is_external,
    is_program_live,
    has_program_page,
    is_program_page_live,
    has_course,
    has_course_run,
    start_date,
    enrollment_end_date,
):
    """
    Test that sort_catalog_pages removes program/course/external course pages that do not have a future start date
    or enrollment end date, and returns appropriately sorted lists of pages
    """
    program = ProgramFactory.create(live=is_program_live, page=None)
    if has_program_page:
        (
            ExternalProgramPageFactory.create(
                program=program, live=is_program_page_live
            )
            if is_external
            else ProgramPageFactory.create(program=program, live=is_program_page_live)
        )

    if has_course:
        course = CourseFactory.create(program=program, is_external=is_external)

        if has_course_run:
            CourseRunFactory.create(
                course=course,
                start_date=start_date,
                enrollment_end=enrollment_end_date,
            )

    if (
        is_program_live
        and has_program_page
        and is_program_page_live
        and has_course
        and has_course_run
        and (
            (start_date is not None and start_date > now_in_utc())
            or (enrollment_end_date is not None and enrollment_end_date > now_in_utc())
        )
    ):
        assert len(ProgramPageProvider().get_data()) == 1
    else:
        assert len(ProgramPageProvider().get_data()) == 0


@pytest.mark.parametrize("is_external", [True, False])
@pytest.mark.parametrize("is_course_live", [True, False])
@pytest.mark.parametrize("has_course_page", [True, False])
@pytest.mark.parametrize("is_course_page_live", [True, False])
@pytest.mark.parametrize("has_course_run", [True, False])
@pytest.mark.parametrize(
    "start_date",
    [None, now_in_utc() + timedelta(days=1), now_in_utc() - timedelta(days=1)],
)
@pytest.mark.parametrize(
    "enrollment_end_date",
    [None, now_in_utc() + timedelta(days=1), now_in_utc() - timedelta(days=1)],
)
def test_filter_course_pages(  # noqa: PLR0913
    is_external,
    is_course_live,
    has_course_page,
    is_course_page_live,
    has_course_run,
    start_date,
    enrollment_end_date,
):
    """
    Test that sort_catalog_pages removes program/course/external course pages that do not have a future start date
    or enrollment end date, and returns appropriately sorted lists of pages
    """
    course = CourseFactory.create(live=is_course_live, page=None)
    if has_course_page:
        (
            ExternalCoursePageFactory.create(course=course, live=is_course_page_live)
            if is_external
            else CoursePageFactory.create(course=course, live=is_course_page_live)
        )
    if has_course_run:
        CourseRunFactory.create(
            course=course,
            start_date=start_date,
            enrollment_end=enrollment_end_date,
        )
    if (
        is_course_live
        and has_course_page
        and is_course_page_live
        and has_course_run
        and (
            (start_date is not None and start_date > now_in_utc())
            or (enrollment_end_date is not None and enrollment_end_date > now_in_utc())
        )
    ):
        assert len(CoursePageProvider().get_data()) == 1
    else:
        assert len(CoursePageProvider().get_data()) == 0
