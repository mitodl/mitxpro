"""Django admin functionality that is relevant to the entire app"""
from django.contrib import admin


class AuditableModelAdmin(admin.ModelAdmin):
    """A ModelAdmin which will save and log"""

    def save_model(self, request, obj, form, change):
        obj.save_and_log(request.user)


class SingletonModelAdmin(admin.ModelAdmin):
    """A ModelAdmin which enforces a singleton model"""

    def has_add_permission(self, request):
        """Overridden method - prevent adding an object if one already exists"""
        return self.model.objects.count() == 0


class TimestampedModelAdmin(admin.ModelAdmin):
    """
    A ModelAdmin that includes timestamp fields in the detail view and, optionally, in the list view
    """

    include_timestamps_in_list = False
    include_created_on_in_list = False

    @staticmethod
    def _join_and_dedupe(existing_field_names, field_names_to_add):
        """
        Joins two tuples of field names together, and ensures that no duplicate field names are added

        Args:
            existing_field_names (Tuple[str]): Field names
            field_names_to_add (Tuple[str]): Field names to add to the existing ones

        Returns:
            Tuple[str]: The combined field names without any duplicates, unless there were any duplicates in the
                tuple of existing field names
        """
        return existing_field_names + tuple(
            field for field in field_names_to_add if field not in existing_field_names
        )

    def get_list_display(self, request):
        list_display = tuple(super().get_list_display(request) or ())
        added_fields = ()
        if self.include_timestamps_in_list:
            added_fields += ("created_on", "updated_on")
        elif self.include_created_on_in_list:
            added_fields += ("created_on",)
        return self._join_and_dedupe(list_display, added_fields)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj=obj) or ())
        if obj is None:
            return readonly_fields
        return self._join_and_dedupe(readonly_fields, ("created_on", "updated_on"))

    def get_exclude(self, request, obj=None):
        exclude = tuple(super().get_exclude(request, obj=obj) or ())
        return self._join_and_dedupe(exclude, ("created_on", "updated_on"))
