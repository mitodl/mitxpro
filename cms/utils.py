"""utils for cms"""
from wagtail.core.models import Site, Page


def get_sort_keys(page):
    """Key function for returning keys for sorting."""

    return page.product.next_run_date, page.is_course_page, page.title


def sort_and_filter_pages(pages):
    """
    Get list of pages and return sorted and filtered list. It will sort page
    based on start_date, type and title.
    """

    return sorted(
        [page for page in pages if page.product.next_run_date], key=get_sort_keys
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
