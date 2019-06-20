"""Tests for CMS views"""
from datetime import timedelta

import pytest

from cms.factories import CoursePageFactory, ProgramPageFactory
from cms.utils import sort_and_filter_pages
from courses.factories import CourseFactory, CourseRunFactory, ProgramFactory
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db


def test_sort_and_filter_pages():
    """
    Test that method exclude pages where start_date is not available.
    """
    first_program = ProgramFactory(title="first program")
    second_program = ProgramFactory(title="second program")

    expired_course = CourseFactory.create(title="expired course")
    CourseRunFactory.create_batch(2, course=expired_course, past_start=True, live=True)

    now = now_in_utc()
    first_course = CourseFactory.create(title="first course", program=first_program)
    CourseRunFactory.create(
        course=first_course, start_date=(now + timedelta(hours=1)), live=True
    )

    second_course = CourseFactory.create(title="second course", program=second_program)
    CourseRunFactory.create(
        course=second_course, start_date=(now + timedelta(hours=2)), live=True
    )

    expired_course_page = CoursePageFactory.create(course=expired_course)
    first_course_page = CoursePageFactory.create(course=first_course)
    second_course_page = CoursePageFactory.create(course=second_course)
    first_program_page = ProgramPageFactory.create(program=first_program)
    second_program_page = ProgramPageFactory.create(program=second_program)

    sorted_pages = sort_and_filter_pages(
        [
            expired_course_page,
            first_course_page,
            second_course_page,
            second_program_page,
            first_program_page,
        ]
    )

    # assert expired_course_pages are filtered out
    assert expired_course_page not in sorted_pages

    # assert program should appear before course with same start date
    assert sorted_pages.index(first_program_page) < sorted_pages.index(
        first_course_page
    )

    # assert pages are sorted on start_date
    assert sorted_pages.index(first_course_page) < sorted_pages.index(
        second_course_page
    )

    # assert if stat_date is same, pages should be sorted by title.
    assert sorted_pages.index(first_program_page) < sorted_pages.index(
        second_program_page
    )
