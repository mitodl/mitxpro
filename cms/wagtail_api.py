from django.db.models import F
from rest_framework.permissions import IsAdminUser
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet

from .wagtail_api_filters import ReadableIDFilter


class AdminOnlyViewSetMixin:
    permission_classes = (IsAdminUser,)


class CustomPagesAPIViewSet(AdminOnlyViewSetMixin, PagesAPIViewSet):
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
        queryset = super().get_queryset()
        model_type = self.request.GET.get("type", None)
        if model_type == "cms.CoursePage":
            queryset = queryset.annotate(readable_id=F("course__readable_id"))
        return queryset


class CustomImagesAPIViewSet(AdminOnlyViewSetMixin, ImagesAPIViewSet):
    pass


class CustomDocumentsAPIViewSet(AdminOnlyViewSetMixin, DocumentsAPIViewSet):
    pass


api_router = WagtailAPIRouter("wagtailapi")
api_router.register_endpoint("pages", CustomPagesAPIViewSet)
api_router.register_endpoint("images", CustomImagesAPIViewSet)
api_router.register_endpoint("documents", CustomDocumentsAPIViewSet)
