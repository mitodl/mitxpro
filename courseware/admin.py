"""
Admin site bindings for profiles
"""

from django.contrib import admin

from courseware.models import CoursewareUser, OpenEdxApiAuth


class CoursewareUserAdmin(admin.ModelAdmin):
    """Admin for CoursewareUser"""

    model = CoursewareUser
    search_fields = ["user", "platform"]
    list_filter = ["platform"]


class OpenEdxApiAuthAdmin(admin.ModelAdmin):
    """Admin for OpenEdxApiAuth"""

    model = OpenEdxApiAuth
    search_fields = ["user"]


admin.site.register(CoursewareUser, CoursewareUserAdmin)
admin.site.register(OpenEdxApiAuth, OpenEdxApiAuthAdmin)
