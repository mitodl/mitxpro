"""
Customize the Wagtail API viewsets to allow public access
and to add additional filtering and metadata fields.
"""

from django.db.models import F
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet

from .filters import ReadableIDFilter
from .permissions import IsCmsStaffOrSuperuser


class CmsPermissionViewSetMixin:
    """
    Mixin to require CMS-level access for API endpoints.
    """

    permission_classes = (IsCmsStaffOrSuperuser,)


class CustomPagesAPIViewSet(CmsPermissionViewSetMixin, PagesAPIViewSet):
    """
    Custom API viewset for Wagtail pages with
    additional filtering and metadata fields.
    """

    filter_backends = [ReadableIDFilter, *PagesAPIViewSet.filter_backends]
    meta_fields = [*PagesAPIViewSet.meta_fields, "live", "last_published_at"]
    listing_default_fields = [
        *PagesAPIViewSet.listing_default_fields,
        "live",
        "last_published_at",
    ]
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        ["readable_id"]
    )

    def get_queryset(self):
        """
        Returns the queryset for the API viewset, with additional annotations
        for annotation_key based on the page type.
        """
        queryset = super().get_queryset()
        annotation_map = {
            "cms.CoursePage": "course",
            "cms.ExternalCoursePage": "course",
            "cms.ProgramPage": "program",
            "cms.ExternalProgramPage": "program",
        }

        model_type = self.request.GET.get("type")
        annotation_key = self.request.GET.get("annotation", "readable_id")

        if model_type in annotation_map:
            queryset = queryset.annotate(
                **{annotation_key: F(f"{annotation_map[model_type]}__{annotation_key}")}
            )

        return queryset


class CustomImagesAPIViewSet(CmsPermissionViewSetMixin, ImagesAPIViewSet):
    """
    Custom API viewset for Wagtail images, publicly available.
    """


class CustomDocumentsAPIViewSet(CmsPermissionViewSetMixin, DocumentsAPIViewSet):
    """
    Custom API viewset for Wagtail documents, publicly available.
    """
