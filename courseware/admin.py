"""
Admin site bindings for profiles
"""

from django.contrib import admin

from courseware.models import CoursewareUser, OpenEdxApiAuth


class CoursewareUserAdmin(admin.ModelAdmin):
    """Admin for CoursewareUser"""

    model = CoursewareUser
    search_fields = ["user__username", "user__email", "user__name", "platform"]
    list_display = ["id", "user", "has_been_synced", "platform"]
    list_filter = ["has_been_synced", "platform"]
    raw_id_fields = ["user"]

    def get_queryset(self, request):
        """Overrides base queryset"""
        return super().get_queryset(request).select_related("user")


class OpenEdxApiAuthAdmin(admin.ModelAdmin):
    """Admin for OpenEdxApiAuth"""

    model = OpenEdxApiAuth
    list_display = ["id", "user"]
    search_fields = ["user__username", "user__email", "user__name"]
    raw_id_fields = ["user"]

    def get_queryset(self, request):
        """Overrides base queryset"""
        return super().get_queryset(request).select_related("user")


admin.site.register(CoursewareUser, CoursewareUserAdmin)
admin.site.register(OpenEdxApiAuth, OpenEdxApiAuthAdmin)
