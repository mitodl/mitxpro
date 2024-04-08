"""Wagtail admin views"""
from wagtail.admin.views.generic.models import IndexView, InspectView
from wagtail.admin.viewsets.base import ViewSetGroup
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permissions import ModelPermissionPolicy

from ecommerce.models import Product, ProductVersion


class CreateOnlyModelPermissionPolicy(ModelPermissionPolicy):
    """
    ModelPermissionPolicy to allow `add` permission.

    Wagtail does not support a separate permission to allow read only mode.
    The reason behind trying to go with a read-only mode is to avoid confusion
    and allow only a single place to change the price of Products.
    """

    def user_has_permission(self, user, action):
        """
        Allows `add` permission
        """
        if action in ("change", "delete"):
            return False
        return super().user_has_permission(user, action)


class AbstractReadOnlyIndexView(IndexView):
    """
    Abstract IndexView to override the edit URL with read only inspect URL.
    """

    def get_edit_url(self, instance):
        """
        Returns inspect URL as we have disabled the edit permissions for the Product and ProductVersion.
        """
        return self.get_inspect_url(instance)


class ProductVersionReadOnlyIndexView(AbstractReadOnlyIndexView):
    """
    ReadOnly IndexView for ProductVersion.
    """

    model = ProductVersion


class ProductReadOnlyIndexView(AbstractReadOnlyIndexView):
    """
    ReadOnly IndexView for Product. Overrides the default queryset to list in-active products.
    """

    model = Product
    queryset = Product.all_objects


class ProductInspectView(InspectView):
    """
    InspectView for Product.
    """

    def get_object(self, queryset=None):
        """
        Get the object using the custom Product manager. By default, `get_object` uses the default manager.
        """
        return Product.all_objects.get(id=self.pk)


class ProductViewSet(ModelViewSet):
    """Wagtail ModelViewSet for Product"""

    index_view_class = ProductReadOnlyIndexView
    inspect_view_class = ProductInspectView
    model = Product
    search_fields = (
        "courseruns__title",
        "programs__title",
        "courseruns__courseware_id",
        "programs__readable_id",
    )
    form_fields = (
        "id",
        "content_type",
        "object_id",
        "is_active",
        "is_private",
    )
    list_display = ("id", "content_object", "is_active", "price")
    list_filter = (
        "is_active",
        "content_type",
    )
    inspect_view_enabled = True
    icon = "pilcrow"

    @property
    def permission_policy(self):
        """
        Custom permission policy disables `change` and `delete` permissions.
        """
        return CreateOnlyModelPermissionPolicy(self.model)


class ProductVersionViewSet(ModelViewSet):
    """Wagtail ModelViewSet for ProductVersion"""

    index_view_class = ProductVersionReadOnlyIndexView
    model = ProductVersion
    search_fields = (
        "text_id",
        "description",
        "product__courseruns__title",
        "product__programs__title",
        "product__courseruns__courseware_id",
        "product__programs__readable_id",
    )
    form_fields = (
        "id",
        "product",
        "price",
        "description",
        "text_id",
        "requires_enrollment_code",
    )
    list_display = (
        "id",
        "product_id",
        "text_id",
        "price",
        "description",
    )
    inspect_view_enabled = True
    icon = "pilcrow"

    @property
    def permission_policy(self):
        """
        Custom permission policy disables `change` and `delete` permissions.
        """
        return CreateOnlyModelPermissionPolicy(self.model)


class ProductViewSetGroup(ViewSetGroup):
    """
    ViewSetGroup to group `Product` and `ProductVersion` views.
    """

    menu_label = "Products"
    menu_icon = "pilcrow"
    items = (ProductViewSet, ProductVersionViewSet)
