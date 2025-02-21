"""
Custom URLs for serving Wagtail pages

NOTE:
These definitions are needed because we want to serve pages at URLs that match
edX course ids, and those edX course ids contain characters that do not match Wagtail's
expected URL pattern (https://github.com/wagtail/wagtail/blob/a657a75/wagtail/core/urls.py)

Example: "course-v1:edX+DemoX+Demo_Course" - Wagtail's pattern does not match the ":" or
the "+" characters.

The pattern(s) defined here serve the same Wagtail view that the library-defined pattern serves.
"""

from django.urls import re_path
from wagtail import views
from wagtail.coreutils import WAGTAIL_APPEND_SLASH
from wagtail.api.v2.router import WagtailAPIRouter

from cms.constants import COURSE_INDEX_SLUG, PROGRAM_INDEX_SLUG, WEBINAR_INDEX_SLUG
from cms.wagtail_api import (
    CustomPagesAPIViewSet,
    CustomImagesAPIViewSet,
    CustomDocumentsAPIViewSet,
)

api_router = WagtailAPIRouter("wagtailapi")
api_router.register_endpoint("pages", CustomPagesAPIViewSet)
api_router.register_endpoint("images", CustomImagesAPIViewSet)
api_router.register_endpoint("documents", CustomDocumentsAPIViewSet)

index_page_pattern = (
    rf"(?:{COURSE_INDEX_SLUG}|{PROGRAM_INDEX_SLUG}|{WEBINAR_INDEX_SLUG})"
)
detail_path_char_pattern = r"\w\-+:"

if WAGTAIL_APPEND_SLASH:
    custom_serve_pattern = (
        r"^({index_page_pattern}/(?:[{resource_pattern}]+/)*)$".format(  # noqa: UP032
            index_page_pattern=index_page_pattern,
            resource_pattern=detail_path_char_pattern,
        )
    )
else:
    custom_serve_pattern = r"^({index_page_pattern}/[{resource_pattern}/]*)$".format(  # noqa: UP032
        index_page_pattern=index_page_pattern, resource_pattern=detail_path_char_pattern
    )


urlpatterns = [re_path(custom_serve_pattern, views.serve, name="wagtail_serve_custom")]
