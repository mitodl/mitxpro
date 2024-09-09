"""API for the CMS app"""

import itertools
import logging
from datetime import MAXYEAR, UTC, datetime

from django.contrib.contenttypes.models import ContentType
from wagtail.models import Page, Site

from cms import models as cms_models
from cms.constants import CERTIFICATE_INDEX_SLUG, ENTERPRISE_PAGE_SLUG

log = logging.getLogger(__name__)
DEFAULT_HOMEPAGE_PROPS = dict(title="Home Page", subhead="This is the home page")  # noqa: C408
DEFAULT_SITE_PROPS = dict(hostname="localhost", port=80)  # noqa: C408


def filter_and_sort_catalog_pages(
    program_pages,
    course_pages,
    external_course_pages,
    external_program_pages,
    sort_by=None,
):
    """
    Filters program and course pages to only include those that should be visible in the catalog, then returns a tuple
    of sorted lists of pages

    Args:
        program_pages (iterable of ProgramPage): ProgramPages to filter and sort
        course_pages (iterable of CoursePage): CoursePages to filter and sort
        external_course_pages (iterable of ExternalCoursePage): ExternalCoursePages to filter and sort
        external_program_pages (iterable of ExternalProgramPage): ExternalProgramPages to filter and sort
        sort_by (str): Sort catalog option.

    Returns:
        tuple of (list of Pages): A tuple containing a list of combined ProgramPages, CoursePages, ExternalCoursePages and ExternalProgramPages, a list of
            ProgramPages and ExternalProgramPages, and a list of CoursePages and ExternalCoursePages, all sorted by the next course/program run date and title
    """
    all_program_pages = program_pages + external_program_pages
    all_course_pages = course_pages + external_course_pages

    valid_program_pages = [
        page for page in all_program_pages if page.product.is_catalog_visible
    ]
    valid_course_pages = [
        page for page in all_course_pages if page.product.is_catalog_visible
    ]

    page_run_dates = {
        page: page.product.next_run_date
        or datetime(year=MAXYEAR, month=1, day=1, tzinfo=UTC)
        for page in itertools.chain(
            valid_program_pages,
            valid_course_pages,
        )
    }
    sorting_key_map = {
        "price_asc": {
            "sort_key": None,
            "reverse": False,
        },
        "price_desc": {
            "sort_key": None,
            "reverse": True,
        },
        "start_date_asc": {
            "sort_key": None,
            "reverse": False,
        },
    }
    sorting = sorting_key_map[sort_by] if sort_by else None  # noqa: F841
    return (
        sorted(
            valid_program_pages + valid_course_pages,
            # ProgramPages with the same next run date as a CoursePage should be sorted first
            key=lambda page: (
                page_run_dates[page],
                page.is_course_page or page.is_external_course_page,
                page.title,
            ),
        ),
        sorted(
            valid_program_pages,
            key=lambda page: (page_run_dates[page], page.title),
        ),
        sorted(
            valid_course_pages,
            key=lambda page: (page_run_dates[page], page.title),
        ),
    )


def get_home_page():
    """
    Returns an instance of the home page (all of our Wagtail pages are expected to be descendants of this home page)

    Returns:
        Page: The home page object
    """
    return Page.objects.get(
        content_type=ContentType.objects.get_for_model(cms_models.HomePage)
    )


def ensure_home_page_and_site():
    """
    Ensures that Wagtail is configured with a home page of the right type, and that
    the home page is configured as the default site.
    """
    site = Site.objects.filter(is_default_site=True).first()
    valid_home_page = Page.objects.filter(
        content_type=ContentType.objects.get_for_model(cms_models.HomePage)
    ).first()
    root = Page.objects.get(depth=1)
    if valid_home_page is None:
        valid_home_page = cms_models.HomePage(**DEFAULT_HOMEPAGE_PROPS)
        root.add_child(instance=valid_home_page)
        valid_home_page.refresh_from_db()
    if site is None:
        Site.objects.create(
            is_default_site=True, root_page=valid_home_page, **DEFAULT_SITE_PROPS
        )
    elif site.root_page is None or site.root_page != valid_home_page:
        site.root_page = valid_home_page
        site.save()
        log.info("Updated site: %s", site)
    wagtail_default_home_page = Page.objects.filter(
        depth=2, content_type=ContentType.objects.get_for_model(Page)
    ).first()
    if wagtail_default_home_page is not None:
        wagtail_default_home_page.delete()


def ensure_catalog_page():
    """
    Ensures that a catalog page with the correct slug exists. If this page doesn't
    exist with the correct slug, the course catalog cannot be accessed.
    """
    catalog_page = Page.objects.filter(
        content_type=ContentType.objects.get_for_model(cms_models.CatalogPage)
    ).first()
    if catalog_page is not None and catalog_page.slug != "catalog":
        catalog_page.delete()
        catalog_page = None
    if catalog_page is None:
        catalog_page = cms_models.CatalogPage(title="Catalog")
        home_page = get_home_page()
        home_page.add_child(instance=catalog_page)
        catalog_page.refresh_from_db()


def ensure_index_pages():  # noqa: C901
    """
    Ensures that the proper index pages exist as children of the home page, and that
    any pages that should belong to those index pages are set as children.
    """
    home_page = get_home_page()
    course_index = cms_models.CourseIndexPage.objects.first()
    program_index = cms_models.ProgramIndexPage.objects.first()
    signatory_index = cms_models.SignatoryIndexPage.objects.first()
    certificate_index = cms_models.CertificateIndexPage.objects.first()
    webinar_index = cms_models.WebinarIndexPage.objects.first()
    blog_index = cms_models.BlogIndexPage.objects.first()

    if not course_index:
        course_index = cms_models.CourseIndexPage(title="Courses")
        home_page.add_child(instance=course_index)

    if course_index.get_children_count() != cms_models.CoursePage.objects.count():
        for course_page in cms_models.CoursePage.objects.all():
            course_page.move(course_index, "last-child")
        log.info("Moved course pages under course index page")

    if not program_index:
        program_index = cms_models.ProgramIndexPage(title="Programs")
        home_page.add_child(instance=program_index)

    if program_index.get_children_count() != cms_models.ProgramPage.objects.count():
        for program_page in cms_models.ProgramPage.objects.all():
            program_page.move(program_index, "last-child")
        log.info("Moved program pages under program index page")

    if not signatory_index:
        signatory_index = cms_models.SignatoryIndexPage(title="Signatories")
        home_page.add_child(instance=signatory_index)

    if signatory_index.get_children_count() != cms_models.SignatoryPage.objects.count():
        for signatory_page in cms_models.SignatoryPage.objects.all():
            signatory_page.move(signatory_index, "last-child")
        log.info("Moved signatory pages under signatory index page")

    if not certificate_index:
        cert_index_content_type, _ = ContentType.objects.get_or_create(
            app_label="cms", model="certificateindexpage"
        )
        certificate_index = cms_models.CertificateIndexPage(
            title="Certificate Index Page",
            content_type_id=cert_index_content_type.id,
            slug=CERTIFICATE_INDEX_SLUG,
        )
        home_page.add_child(instance=certificate_index)

    if not webinar_index:
        webinar_index = cms_models.WebinarIndexPage(title="Webinars")
        home_page.add_child(instance=webinar_index)

    if webinar_index.get_children_count() != cms_models.WebinarPage.objects.count():
        for webinar_page in cms_models.WebinarPage.objects.all():
            webinar_page.move(webinar_index, "last-child")
        log.info("Moved webinar pages under webinar index page")

    if not blog_index:
        blog_index = cms_models.BlogIndexPage(title="Blog")
        home_page.add_child(instance=blog_index)


def ensure_enterprise_page():
    """
    Ensure that an enterprise page with the correct slug exists.
    """
    enterprise_page = cms_models.EnterprisePage.objects.first()

    if enterprise_page and enterprise_page.slug == ENTERPRISE_PAGE_SLUG:
        return

    enterprise_page_data = {
        "title": "Enterprise Page",
        "slug": ENTERPRISE_PAGE_SLUG,
        "description": "Deepen your team's career knowledge and expand their abilities with MIT xPRO's online "
        "courses for professionals.",
        "action_title": "Find out what MIT xPRO can do for your team.",
        "headings": [
            {
                "type": "heading",
                "value": {
                    "upper_head": "THE BEST COMPANIES",
                    "middle_head": "CONNECT WITH",
                    "bottom_head": "THE BEST MINDS AT MIT",
                },
            },
        ],
    }
    enterprise_page = cms_models.EnterprisePage(**enterprise_page_data)
    home_page = get_home_page()
    home_page.add_child(instance=enterprise_page)


def configure_wagtail():
    """
    Ensures that all appropriate changes have been made to Wagtail that will
    make the site navigable.
    """
    ensure_home_page_and_site()
    ensure_catalog_page()
    ensure_index_pages()
    ensure_enterprise_page()
