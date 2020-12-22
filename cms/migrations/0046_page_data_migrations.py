"""
Data migration to do the following:

1) Ensure the correct state for course/program index pages and correct depth for course/program detail pages
2) Ensure that a catalog page exists in the right place
3) Ensure that a certificate index page exists in the right place

NOTE: Data migrations are liable to fail if the Wagtail Page model (or potentially other Wagtail models) are changed
from version to version. In those cases, we can set the existing data migration(s) to be a no-op in both directions,
then create a new data migration with the same contents, and add the relevant Wagtail migration as a dependency.
"""
import datetime
import json

import pytz
from django.db import migrations
from wagtail.core.models import Page, PageRevision

COURSE_INDEX_PAGE_PROPERTIES = dict(title="Courses")
PROGRAM_INDEX_PAGE_PROPERTIES = dict(title="Programs")
CERTIFICATE_INDEX_SLUG = "certificate"


def now_in_utc():
    """
    Get the current time in UTC

    Returns:
        datetime.datetime: A datetime object for the current time
    """
    return datetime.datetime.now(tz=pytz.UTC)


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


def get_home_page(apps):
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


def create_index_pages_and_nest_detail(apps, schema_editor):
    """
    Create index pages for courses and programs and move the respective
    course and program pages under these index pages.
    """
    from cms.models import CourseIndexPage, ProgramIndexPage

    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")

    # Home page
    home_page = get_home_page(apps)

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


def unnest_detail_and_delete_index_pages(apps, schema_editor):
    """
    Move course and program pages under the home page and remove index pages.
    """
    CourseIndexPage = apps.get_model("cms", "CourseIndexPage")
    ProgramIndexPage = apps.get_model("cms", "ProgramIndexPage")
    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")

    # Move course/program detail pages to be children of the home page
    home_page = get_home_page(apps)
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


def create_catalog_page(apps, schema_editor):
    """
    Create a catalog page under the home page
    """
    CatalogPage = apps.get_model("cms", "CatalogPage")
    ContentType = apps.get_model("contenttypes.ContentType")
    catalog_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="catalogpage"
    )
    home_page = get_home_page(apps)

    catalog = CatalogPage.objects.first()
    if not catalog:
        catalog_page_content = dict(
            title="Courseware Catalog",
            content_type_id=catalog_content_type.id,
            slug="catalog",
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


def remove_catalog_page(apps, schema_editor):
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


def create_certificate_index_page(apps, schema_editor):
    """
    Create a certificate index page under the home page
    """
    CertificateIndexPage = apps.get_model("cms", "CertificateIndexPage")
    ContentType = apps.get_model("contenttypes.ContentType")
    index_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="certificateindexpage"
    )
    home_page = get_home_page(apps)

    index_page = CertificateIndexPage.objects.first()

    if not index_page:
        index_page_content = dict(
            title="Certificate Index Page",
            content_type_id=index_content_type.id,
            slug=CERTIFICATE_INDEX_SLUG,
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


def remove_certificate_index_page(apps, schema_editor):
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


def migrate_data(apps, schema_editor):
    """
    Apply all data migrations in order
    """
    create_index_pages_and_nest_detail(apps, schema_editor)
    create_catalog_page(apps, schema_editor)
    create_certificate_index_page(apps, schema_editor)


def reverse_migrate_data(apps, schema_editor):
    """
    Reverse all data migrations in the opposite order from which they were applied
    """
    remove_certificate_index_page(apps, schema_editor)
    remove_catalog_page(apps, schema_editor)
    unnest_detail_and_delete_index_pages(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0045_assign_unlock_grouppagepermission"),
        ("cms", "0045_certificate_page_courserun_overrides"),
    ]

    operations = [migrations.RunPython(migrate_data, reverse_migrate_data)]
