"""
Admin site bindings for profiles
"""

from django.contrib import admin

from .models import Program, Course, CourseRun, ProgramEnrollment, CourseRunEnrollment


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


class ProgramEnrollmentAdmin(admin.ModelAdmin):
    """Admin for ProgramEnrollment"""

    model = ProgramEnrollment

    def get_queryset(self, request):
        """
        Overrides base method. A filter was applied to the default queryset, so
        this method ensures that Django admin uses an unfiltered queryset.
        """
        qs = self.model.all_objects.get_queryset()
        # Code below was copied/pasted from the base method
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        """
        Saves object and logs change to object
        """
        obj.save_and_log(request.user)


class CourseRunEnrollmentAdmin(admin.ModelAdmin):
    """Admin for CourseRunEnrollment"""

    model = CourseRunEnrollment

    def get_queryset(self, request):
        """
        Overrides base method. A filter was applied to the default queryset, so
        this method ensures that Django admin uses an unfiltered queryset.
        """
        qs = self.model.all_objects.get_queryset()
        # Code below was copied/pasted from the base method
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        """
        Saves object and logs change to object
        """
        obj.save_and_log(request.user)


admin.site.register(Program, ProgramAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(CourseRun, CourseRunAdmin)
admin.site.register(ProgramEnrollment, ProgramEnrollmentAdmin)
admin.site.register(CourseRunEnrollment, CourseRunEnrollmentAdmin)
