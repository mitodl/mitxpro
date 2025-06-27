"""Custom hooks to configure wagtail behavior"""

from django.contrib.contenttypes.models import ContentType
from wagtail import hooks
from wagtail.admin.api.views import PagesAdminAPIViewSet

from cms.models import ExternalCoursePage
from cms.utils import (
    create_and_add_b2b_section,
    create_and_add_how_you_will_learn_section,
)
from courses.models import CourseRun, Program
from ecommerce.models import Product, ProductVersion


@hooks.register("construct_explorer_page_queryset")
def sort_pages_alphabetically(
    parent_page,  # noqa: ARG001
    pages,
    request,  # noqa: ARG001
):
    """Sort all pages by title alphabetically"""
    return pages.order_by("title")


class OrderedPagesAPIEndpoint(PagesAdminAPIViewSet):
    """A clone of the default Wagtail admin API that additionally orders all responses by page title alphabetically"""

    def filter_queryset(self, queryset):
        """Sort all pages by title alphabetically"""
        return super().filter_queryset(queryset).order_by("title")


@hooks.register("construct_admin_api")
def configure_admin_api_default_order(router):
    """Swap admin pages API for our own flavor that orders results by title"""
    router.register_endpoint("pages", OrderedPagesAPIEndpoint)


@hooks.register("after_publish_page")
def create_product_and_versions_for_courseware_pages(request, page):
    """
    Creates Product and Product Version for the courseware pages on page publish.
    """
    if not (
        hasattr(page, "is_internal_or_external_course_page")
        or hasattr(page, "is_internal_or_external_program_page")
    ):
        return

    form_class = page.specific_class.get_edit_handler().get_form_class()
    form = form_class(request.POST, instance=page)
    if not form.is_valid():
        return

    course_run_id = form.cleaned_data["course_run"]
    price = form.cleaned_data["price"]

    if page.is_internal_or_external_course_page and course_run_id and price:
        course_run = CourseRun.objects.get(id=course_run_id)
        if course_run.current_price != price:
            product, _ = Product.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(CourseRun),
                object_id=course_run.id,
            )
            ProductVersion.objects.create(
                product=product, price=price, description=course_run.text_id
            )

    elif (
        page.is_internal_or_external_program_page
        and price != page.program.current_price
    ):
        product, _ = Product.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Program),
            object_id=page.program.id,
        )
        ProductVersion.objects.create(
            product=product, price=price, description=page.program.text_id
        )


@hooks.register("after_create_page")
def create_common_child_pages_for_external_courses(request, page):  # noqa: ARG001
    """
    Automatically creates static sections ("How You Will Learn" and "For Teams")
    for newly created ExternalCoursePage instances.

    Args:
        request: The HTTP request that triggered the page creation.
        page: The newly created page. Static sections are created only if the page
              is an instance of `ExternalCoursePage`.
    """
    if not isinstance(page, ExternalCoursePage):
        # We need to create sections only for External Course Pages
        return

    platform = page.course.platform.name
    create_and_add_how_you_will_learn_section(page, platform)
    create_and_add_b2b_section(page, platform)


@hooks.register("insert_editor_js")
def conditional_certificate_fields():
    return '<script src="/static/js/certificate_admin.js"></script>'
