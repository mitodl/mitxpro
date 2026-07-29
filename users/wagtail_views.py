"""Wagtail admin views for the users app"""

from wagtail.users.views.users import (
    IndexView as WagtailUserIndexView,
    UserViewSet as WagtailUserViewSet,
)


class UserIndexView(WagtailUserIndexView):
    """
    Custom IndexView for the mitxpro User model.

    The mitxpro User model uses a single `name` field instead of the standard
    Django `first_name` / `last_name` fields. Wagtail 6.x's built-in
    order_queryset() maps ordering="name" to order_by("last_name", "first_name"),
    which raises a FieldError. This overrides that behaviour.
    """

    def order_queryset(self, queryset):
        ordering = self.ordering
        if ordering in ("name", "-name"):
            return queryset.order_by(ordering)
        return super().order_queryset(queryset)


class UserViewSet(WagtailUserViewSet):
    index_view_class = UserIndexView
