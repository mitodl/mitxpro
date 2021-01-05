"""Custom hooks to configure wagtail behavior"""
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.core import hooks


@hooks.register("construct_explorer_page_queryset")
def sort_pages_alphabetically(
    parent_page, pages, request
):  # pylint: disable=unused-argument
    """Sort all pages by title alphabetically"""
    return pages.order_by("title")


class OrderedPagesAPIEndpoint(PagesAPIViewSet):
    """A clone of the default Wagtail admin API that additionally orders all responses by page title alphabetically"""

    def filter_queryset(self, queryset):
        """Sort all pages by title alphabetically"""
        return super().filter_queryset(queryset).order_by("title")


@hooks.register("construct_admin_api")
def configure_admin_api_default_order(api_router):
    """Swap admin pages API for our own flavor that orders results by title"""
    api_router = WagtailAPIRouter("wagtailapi")
    api_router.register_endpoint("pages", OrderedPagesAPIEndpoint)
    return api_router
