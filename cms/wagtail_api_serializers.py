from rest_framework.fields import Field

from wagtail.models import Page
from wagtail.api.v2.serializers import get_serializer_class
from wagtail.api.v2.views import PagesAPIViewSet


class ProductChildPageSerializer(Field):
    def to_representation(self, value):
        if hasattr(value, "all"):
            base_context = {"view": PagesAPIViewSet()}
            context = {**base_context, **getattr(self, "context", {})}
            return [self.serialize_page(page, context) for page in value.all()]
        return self.serialize_page(value, self.context)

    def serialize_page(self, page, context):
        if not isinstance(page, Page):
            return None

        model = page.specific.__class__

        serializer = get_serializer_class(
            model,
            PagesAPIViewSet.body_fields + PagesAPIViewSet.meta_fields,
            PagesAPIViewSet.meta_fields,
            base=PagesAPIViewSet.base_serializer_class,
        )

        return serializer(page.specific, context=context).data
