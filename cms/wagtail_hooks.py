"""Custom hooks to configure wagtail behavior"""

from django.contrib.contenttypes.models import ContentType
from wagtail import hooks
from wagtail.admin.api.views import PagesAdminAPIViewSet

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
def create_product_and_product_versions(request, page):
    """
    Creates Product and Product Version for the courseware pages on page publish.
    """
    if not (
        page.is_internal_or_external_course_page
        or page.is_internal_or_external_program_page
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
