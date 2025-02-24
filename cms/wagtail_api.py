"""
Customize the Wagtail API viewsets to restrict access to admin users
and to add additional filtering and metadata fields.
"""

from django.db.models import F
from rest_framework.permissions import IsAdminUser
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet

from .wagtail_api_filters import ReadableIDFilter


class AdminOnlyViewSetMixin:
    """
    Mixin to restrict access to admin users only.
    """

    permission_classes = (IsAdminUser,)


class CustomPagesAPIViewSet(AdminOnlyViewSetMixin, PagesAPIViewSet):
    """
    Custom API viewset for Wagtail pages with additional filtering and metadata fields.
    """

    filter_backends = [ReadableIDFilter] + PagesAPIViewSet.filter_backends
    meta_fields = PagesAPIViewSet.meta_fields + ["live", "last_published_at"]
    listing_default_fields = PagesAPIViewSet.listing_default_fields + [
        "live",
        "last_published_at",
    ]
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        ["readable_id"]
    )

    def get_queryset(self):
        """
        Returns the queryset for the API viewset, with additional annotations
        for readable_id based on the page type.
        """
        queryset = super().get_queryset()
        model_type = self.request.GET.get("type", None)
        if model_type == "cms.CoursePage":
            queryset = queryset.annotate(readable_id=F("course__readable_id"))
        elif model_type == "cms.ProgramPage":
            queryset = queryset.annotate(readable_id=F("program__readable_id"))
        return queryset


class CustomImagesAPIViewSet(AdminOnlyViewSetMixin, ImagesAPIViewSet):
    """
    Custom API viewset for Wagtail images, restricted to admin users.
    """

    pass


class CustomDocumentsAPIViewSet(AdminOnlyViewSetMixin, DocumentsAPIViewSet):
    """
    Custom API viewset for Wagtail documents, restricted to admin users.
    """

    pass
