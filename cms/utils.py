"""utils for cms"""


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
