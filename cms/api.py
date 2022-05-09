"""API for the CMS app"""
import itertools
from datetime import MINYEAR, datetime
import logging
import pytz
import json

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from wagtail.core.models import Page, Site
from cms import models as cms_models
from cms.constants import CERTIFICATE_INDEX_SLUG
from wagtail.core.models import Page, PageRevision

log = logging.getLogger(__name__)
DEFAULT_HOMEPAGE_PROPS = dict(title="Home Page", subhead="This is the home page")
DEFAULT_SITE_PROPS = dict(hostname="localhost", port=80)
COURSE_INDEX_PAGE_PROPERTIES = dict(title="Courses")
PROGRAM_INDEX_PAGE_PROPERTIES = dict(title="Programs")
CERTIFICATE_INDEX_SLUG = "certificate"


def filter_and_sort_catalog_pages(
    program_pages, course_pages, external_course_pages, external_program_pages
):
    """
    Filters program and course pages to only include those that should be visible in the catalog, then returns a tuple
    of sorted lists of pages

    Args:
        program_pages (iterable of ProgramPage): ProgramPages to filter and sort
        course_pages (iterable of CoursePage): CoursePages to filter and sort
        external_course_pages (iterable of ExternalCoursePage): ExternalCoursePages to filter and sort
        external_program_pages (iterable of ExternalProgramPage): ExternalProgramPages to filter and sort

    Returns:
        tuple of (list of Pages): A tuple containing a list of combined ProgramPages, CoursePages, ExternalCoursePages and ExternalProgramPages, a list of
            ProgramPages and ExternalProgramPages, and a list of CoursePages and ExternalCoursePages, all sorted by the next course/program run date and title
    """
    valid_program_pages = [
        page for page in program_pages if page.product.is_catalog_visible
    ]
    valid_course_pages = [
        page for page in course_pages if page.product.is_catalog_visible
    ]

    valid_external_course_pages = list(external_course_pages)

    valid_external_program_pages = list(external_program_pages)

    page_run_dates = {
        page: (
            page.next_run_date if page.is_external_page else page.product.next_run_date
        )
        or datetime(year=MINYEAR, month=1, day=1, tzinfo=pytz.UTC)
        for page in itertools.chain(
            valid_program_pages,
            valid_course_pages,
            valid_external_course_pages,
            valid_external_program_pages,
        )
    }
    return (
        sorted(
            valid_program_pages
            + valid_external_program_pages
            + valid_course_pages
            + valid_external_course_pages,
            # ProgramPages with the same next run date as a CoursePage should be sorted first
            key=lambda page: (
                page_run_dates[page],
                page.is_course_page or page.is_external_course_page,
                page.title,
            ),
        ),
        sorted(
            valid_program_pages + valid_external_program_pages,
            key=lambda page: (page_run_dates[page], page.title),
        ),
        sorted(
            valid_course_pages + valid_external_course_pages,
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


def ensure_index_pages():
    """
    Ensures that the proper index pages exist as children of the home page, and that
    any pages that should belong to those index pages are set as children.
    """
    home_page = get_home_page()
    course_index = cms_models.CourseIndexPage.objects.first()
    program_index = cms_models.ProgramIndexPage.objects.first()
    signatory_index = cms_models.SignatoryIndexPage.objects.first()
    certificate_index = cms_models.CertificateIndexPage.objects.first()

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

    if (
        certificate_index.get_children_count()
        != cms_models.CertificatePage.objects.count()
    ):
        for cert_page in cms_models.CertificatePage.objects.all():
            cert_page.move(certificate_index, "last-child")
        log.info("Moved certificate pages under certificate index page")


def configure_wagtail():
    """
    Ensures that all appropriate changes have been made to Wagtail that will
    make the site navigable.
    """
    migrate_data()
    ensure_home_page_and_site()
    ensure_catalog_page()
    ensure_index_pages()


def now_in_utc():
    """
    Get the current time in UTC

    Returns:
        datetime.datetime: A datetime object for the current time
    """
    return datetime.now(tz=pytz.UTC)


def delete_wagtail_pages(specific_page_cls, filter_dict=None):
    """
    Completely deletes Wagtail CMS pages that match a filter. Wagtail overrides standard delete functionality,
    making it difficult to actually delete Page objects and get information about what was deleted.
    """
    page_ids_to_delete = specific_page_cls.objects.values_list("id", flat=True)
    if filter_dict:
        page_ids_to_delete = page_ids_to_delete.filter(**filter_dict)
    num_pages = len(page_ids_to_delete)
    base_pages_qset = Page.objects.filter(id__in=page_ids_to_delete)
    if not base_pages_qset.exists():
        return 0, {}
    base_pages_qset.delete()
    return (
        num_pages,
        {specific_page_cls._meta.label: num_pages},  # pylint: disable=protected-access
    )


def get_home_page_from_site():
    """
    Importing the Site model from the registry means if we access the root page from this
    model we will get an instance of the Page with only the basic model methods so we simply extract
    the ID of the page and hand it to the Page model imported directly.
    """
    Site = apps.get_model("wagtailcore", "Site")
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


def create_index_pages_and_nest_detail():
    """
    Create index pages for courses and programs and move the respective
    course and program pages under these index pages.
    """
    from cms.models import CourseIndexPage, ProgramIndexPage

    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")

    # Home page
    home_page = get_home_page_from_site()

    course_index = CourseIndexPage.objects.first()
    if not course_index:
        page_obj = CourseIndexPage(**COURSE_INDEX_PAGE_PROPERTIES)
        course_index = home_page.add_child(instance=page_obj)
    program_index = ProgramIndexPage.objects.first()
    if not program_index:
        page_obj = ProgramIndexPage(**PROGRAM_INDEX_PAGE_PROPERTIES)
        program_index = home_page.add_child(instance=page_obj)
    # Move course/program detail pages to be children of the course/program index pages
    for page_id in CoursePage.objects.values_list("id", flat=True):
        page = Page.objects.get(id=page_id)
        page.move(course_index, "last-child")
    for page_id in ProgramPage.objects.values_list("id", flat=True):
        page = Page.objects.get(id=page_id)
        page.move(program_index, "last-child")


def unnest_detail_and_delete_index_pages():
    """
    Move course and program pages under the home page and remove index pages.
    """
    CourseIndexPage = apps.get_model("cms", "CourseIndexPage")
    ProgramIndexPage = apps.get_model("cms", "ProgramIndexPage")
    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")

    # Move course/program detail pages to be children of the home page
    home_page = get_home_page_from_site()
    top_level_child_ids = [child.id for child in home_page.get_children()]
    for page_id in CoursePage.objects.values_list("id", flat=True):
        if page_id not in top_level_child_ids:
            page = Page.objects.get(id=page_id)
            page.move(home_page, "last-child")
    for page_id in ProgramPage.objects.values_list("id", flat=True):
        if page_id not in top_level_child_ids:
            page = Page.objects.get(id=page_id)
            page.move(home_page, "last-child")
    # Remove the course/program index pages
    delete_wagtail_pages(ProgramIndexPage)
    delete_wagtail_pages(CourseIndexPage)


def create_catalog_page():
    """
    Create a catalog page under the home page
    """
    CatalogPage = apps.get_model("cms", "CatalogPage")
    ContentType = apps.get_model("contenttypes.ContentType")
    catalog_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="catalogpage"
    )
    home_page = get_home_page_from_site()

    catalog = CatalogPage.objects.first()
    if not catalog:
        catalog_page_content = dict(
            title="Courseware Catalog",
            content_type_id=catalog_content_type.id,
            slug="catalog",
            locale_id=home_page.get_default_locale().id,
        )
        catalog_page_obj = CatalogPage(**catalog_page_content)
        home_page.add_child(instance=catalog_page_obj)
        # NOTE: This block of code creates page revision and publishes it. There may be an easier way to do this.
        content_json = json.dumps(dict(**catalog_page_content, pk=catalog_page_obj.id))
        revision = PageRevision.objects.create(
            page_id=catalog_page_obj.id,
            submitted_for_moderation=False,
            created_at=now_in_utc(),
            content_json=content_json,
        )
        revision.publish()


def remove_catalog_page():
    """
    Remove the catalog page
    """
    ContentType = apps.get_model("contenttypes.ContentType")
    catalog_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="catalogpage"
    )
    catalog = Page.objects.get(content_type_id=catalog_content_type.id)
    if catalog:
        catalog.delete()


def create_certificate_index_page():
    """
    Create a certificate index page under the home page
    """
    CertificateIndexPage = apps.get_model("cms", "CertificateIndexPage")
    ContentType = apps.get_model("contenttypes.ContentType")
    index_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="certificateindexpage"
    )
    home_page = get_home_page_from_site()

    index_page = CertificateIndexPage.objects.first()

    if not index_page:
        index_page_content = dict(
            title="Certificate Index Page",
            content_type_id=index_content_type.id,
            slug=CERTIFICATE_INDEX_SLUG,
            locale_id=home_page.get_default_locale().id,
        )
        index_page_obj = CertificateIndexPage(**index_page_content)
        home_page.add_child(instance=index_page_obj)
        # NOTE: This block of code creates page revision and publishes it. There may be an easier way to do this.
        content_json = json.dumps(dict(**index_page_content, pk=index_page_obj.id))
        revision = PageRevision.objects.create(
            page_id=index_page_obj.id,
            submitted_for_moderation=False,
            created_at=now_in_utc(),
            content_json=content_json,
        )
        revision.publish()


def remove_certificate_index_page():
    """
    Remove the certificate index page
    """
    ContentType = apps.get_model("contenttypes.ContentType")
    index_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="certificateindexpage"
    )
    index_page = Page.objects.get(content_type_id=index_content_type.id)
    if index_page:
        index_page.delete()


def migrate_data():
    """
    Apply all data migrations in order
    """
    create_index_pages_and_nest_detail()
    create_catalog_page()
    create_certificate_index_page()


def reverse_migrate_data():
    """
    Reverse all data migrations in the opposite order from which they were applied
    """
    remove_certificate_index_page()
    remove_catalog_page()
    unnest_detail_and_delete_index_pages()
