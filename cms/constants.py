"""Constants for the CMS app"""

import enum

COURSE_INDEX_SLUG = "courses"
PROGRAM_INDEX_SLUG = "programs"
SIGNATORY_INDEX_SLUG = "signatories"
CERTIFICATE_INDEX_SLUG = "certificate"
WEBINAR_INDEX_SLUG = "webinars"
BLOG_INDEX_SLUG = "blog"
ENTERPRISE_PAGE_SLUG = "enterprise"
COMMON_COURSEWARE_COMPONENT_INDEX_SLUG = "common-courseware-component-pages"

ALL_TOPICS = "All Topics"
ALL_TAB = "all-tab"

# ************** CONSTANTS FOR WEBINARS **************

UPCOMING_WEBINAR = "UPCOMING"
ON_DEMAND_WEBINAR = "ON-DEMAND"
WEBINAR_DEFAULT_IMAGES = [
    "images/webinars/webinar-default-001.jpg",
    "images/webinars/webinar-default-002.jpg",
    "images/webinars/webinar-default-003.jpg",
    "images/webinars/webinar-default-004.jpg",
    "images/webinars/webinar-default-005.jpg",
]
WEBINAR_HEADER_BANNER = "images/webinars/webinar-header-banner.jpg"
UPCOMING_WEBINAR_BUTTON_TITLE = "RESERVE YOUR SEAT"
ON_DEMAND_WEBINAR_BUTTON_TITLE = "VIEW RECORDING"

FORMAT_ONLINE = "Online"
FORMAT_HYBRID = "Hybrid"
FORMAT_OTHER = "Other"


class CatalogSorting(enum.Enum):
    """Catalog sorting option"""

    BEST_MATCH = ("best_match", "Best Match")
    START_DATE_ASC = ("start_date_asc", "Start Date")
    PRICE_DESC = ("price_desc", "Price: High-Low")
    PRICE_ASC = ("price_asc", "Price: Low-High")

    def __init__(self, sorting_value, sorting_title):
        """
        A sorting option can have a value and a title.
        """
        self.sorting_value = sorting_value
        self.sorting_title = sorting_title
