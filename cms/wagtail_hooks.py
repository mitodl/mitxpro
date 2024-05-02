"""Custom hooks to configure wagtail behavior"""

from wagtail import hooks
from wagtail.admin.api.views import PagesAdminAPIViewSet


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
