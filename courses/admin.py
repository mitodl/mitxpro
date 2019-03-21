"""
Admin site bindings for profiles
"""

from django.contrib import admin

from .models import Program, Course, CourseRun


class ProgramAdmin(admin.ModelAdmin):
    """Admin for Program"""

    model = Program
    search_fields = ["title", "description"]
    list_filter = ["live"]


class CourseAdmin(admin.ModelAdmin):
    """Admin for Course"""

    model = Course
    search_fields = ["title", "description"]
    list_filter = ["live", "program"]


class CourseRunAdmin(admin.ModelAdmin):
    """Admin for CourseRun"""

    model = CourseRun
    search_fields = ["title", "courseware_id"]
    list_filter = ["live", "course"]


admin.site.register(Program, ProgramAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(CourseRun, CourseRunAdmin)
