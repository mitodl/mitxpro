"""
Data migration to ensure the correct state for course/program index pages and
correct depth for course/program detail pages
"""
from django.db import migrations
from wagtail.core.models import Page

COURSE_INDEX_PAGE_PROPERTIES = dict(title="Courses")
PROGRAM_INDEX_PAGE_PROPERTIES = dict(title="Programs")


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


def get_top_level_wagtail_page():
    """
    The Wagtail CMS (at least in our usage) has one root page at depth 1, and one page at depth 2. All pages that we
    create in Wagtail are added as children to the page at depth 2.
    """
    return Page.objects.get(depth=2)


def create_index_pages_and_nest_detail(apps, schema_editor):
    """
    Create index pages for courses and programs and move the respective
    course and program pages under these index pages.
    """
    from cms.models import CourseIndexPage, ProgramIndexPage

    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")

    # Default home page
    top_level_page = get_top_level_wagtail_page()

    course_index = CourseIndexPage.objects.first()
    if not course_index:
        page_obj = CourseIndexPage(**COURSE_INDEX_PAGE_PROPERTIES)
        course_index = top_level_page.add_child(instance=page_obj)
    program_index = ProgramIndexPage.objects.first()
    if not program_index:
        page_obj = ProgramIndexPage(**PROGRAM_INDEX_PAGE_PROPERTIES)
        program_index = top_level_page.add_child(instance=page_obj)
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

    # Move course/program detail pages to be children of the top-level page
    top_level_page = get_top_level_wagtail_page()
    top_level_child_ids = [child.id for child in top_level_page.get_children()]
    for page_id in CoursePage.objects.values_list("id", flat=True):
        if page_id not in top_level_child_ids:
            page = Page.objects.get(id=page_id)
            page.move(top_level_page, "last-child")
    for page_id in ProgramPage.objects.values_list("id", flat=True):
        if page_id not in top_level_child_ids:
            page = Page.objects.get(id=page_id)
            page.move(top_level_page, "last-child")
    # Remove the course/program index pages
    delete_wagtail_pages(ProgramIndexPage)
    delete_wagtail_pages(CourseIndexPage)


class Migration(migrations.Migration):

    dependencies = [("cms", "0027_course_program_index_pages")]

    operations = [
        migrations.RunPython(
            create_index_pages_and_nest_detail, unnest_detail_and_delete_index_pages
        )
    ]
