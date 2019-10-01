"""utils for cms"""
import itertools
import datetime
import pytz
from wagtail.core.models import Site, Page


def filter_and_sort_catalog_pages(program_pages, course_pages):
    """
    Filters program and course pages to only include those that should be visible in the catalog, then returns a tuple
    of sorted lists of pages

    Args:
        program_pages (iterable of ProgramPage): ProgramPages to filter and sort
        course_pages (iterable of CoursePage): CoursePages to filter and sort

    Returns:
        tuple of (list of Pages): A tuple containing a list of combined ProgramPages and CoursePages, a list of
            ProgramPages, and a list of CoursePages, all sorted by the next course run date and title
    """
    valid_program_pages = [
        page for page in program_pages if page.product.is_catalog_visible
    ]
    valid_course_pages = [
        page for page in course_pages if page.product.is_catalog_visible
    ]

    page_run_dates = {
        page: page.product.next_run_date
        or datetime.datetime(year=datetime.MINYEAR, month=1, day=1, tzinfo=pytz.UTC)
        for page in itertools.chain(valid_program_pages, valid_course_pages)
    }
    return (
        sorted(
            valid_program_pages + valid_course_pages,
            # ProgramPages with the same next run date as a CoursePage should be sorted first
            key=lambda page: (page_run_dates[page], page.is_course_page, page.title),
        ),
        sorted(
            valid_program_pages, key=lambda page: (page_run_dates[page], page.title)
        ),
        sorted(valid_course_pages, key=lambda page: (page_run_dates[page], page.title)),
    )


def get_home_page():
    """
    Returns an instance of the home page (all of our Wagtail pages are expected to be descendants of this home page)
    """
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        raise Exception(
            "A default site is not set up. Please setup a default site before running this migration"
        )
    if not site.root_page:
        raise Exception(
            "No root (home) page set up. Please setup a root (home) page for the default site before running this migration"
        )
    return Page.objects.get(id=site.root_page.id)
