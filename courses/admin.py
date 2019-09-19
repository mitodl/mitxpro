"""
Admin site bindings for profiles
"""

from django.contrib import admin

from mitxpro.utils import get_field_names
from .models import (
    Program,
    Course,
    CourseRun,
    ProgramEnrollment,
    CourseRunEnrollment,
    ProgramEnrollmentAudit,
    CourseRunEnrollmentAudit,
    CourseRunGrade,
    CourseRunGradeAudit,
    CourseRunCertificate,
    ProgramCertificate,
)


class ProgramAdmin(admin.ModelAdmin):
    """Admin for Program"""

    model = Program
    search_fields = ["title"]
    list_filter = ["live"]


class CourseAdmin(admin.ModelAdmin):
    """Admin for Course"""

    model = Course
    search_fields = ["title"]
    list_filter = ["live", "program"]


class CourseRunAdmin(admin.ModelAdmin):
    """Admin for CourseRun"""

    model = CourseRun
    search_fields = ["title", "courseware_id"]
    list_filter = ["live", "course"]


class ProgramEnrollmentAdmin(admin.ModelAdmin):
    """Admin for ProgramEnrollment"""

    model = ProgramEnrollment
    search_fields = ["user", "company", "Program"]
    list_filter = ["active", "change_status"]
    list_fields = ["user.email", "change_status"]
    raw_id_fields = ("user","order")

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


class ProgramEnrollmentAuditAdmin(admin.ModelAdmin):
    """Admin for ProgramEnrollmentAudit"""

    model = ProgramEnrollmentAudit
    readonly_fields = get_field_names(ProgramEnrollmentAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunEnrollmentAdmin(admin.ModelAdmin):
    """Admin for CourseRunEnrollment"""

    model = CourseRunEnrollment
    search_fields = ["user", "company", "CourseRun"]
    list_filter = ["active", "change_status"]
    list_fields = ["user.email", "change_status"]
    raw_id_fields = ("user","order")

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


class CourseRunEnrollmentAuditAdmin(admin.ModelAdmin):
    """Admin for CourseRunEnrollmentAudit"""

    model = CourseRunEnrollmentAudit
    readonly_fields = get_field_names(CourseRunEnrollmentAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunGradeAdmin(admin.ModelAdmin):
    """Admin for CourseRunGrade"""

    model = CourseRunGrade


class CourseRunGradeAuditAdmin(admin.ModelAdmin):
    """Admin for CourseRunGradeAudit"""

    model = CourseRunGradeAudit
    readonly_fields = get_field_names(CourseRunGradeAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunCertificateAdmin(admin.ModelAdmin):
    """Admin for CourseRunCertificate"""

    model = CourseRunCertificate
    list_display = ["uuid", "user", "course_run"]
    search_fields = [
        "course_run__courseware_id",
        "course_run__title",
        "user__username",
        "user__email",
    ]


class ProgramCertificateAdmin(admin.ModelAdmin):
    """Admin for ProgramCertificate"""

    model = ProgramCertificate
    list_display = ["uuid", "user", "program"]
    search_fields = [
        "program__readable_id",
        "program__title",
        "user__username",
        "user__email",
    ]


admin.site.register(Program, ProgramAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(CourseRun, CourseRunAdmin)
admin.site.register(ProgramEnrollment, ProgramEnrollmentAdmin)
admin.site.register(ProgramEnrollmentAudit, ProgramEnrollmentAuditAdmin)
admin.site.register(CourseRunEnrollment, CourseRunEnrollmentAdmin)
admin.site.register(CourseRunEnrollmentAudit, CourseRunEnrollmentAuditAdmin)
admin.site.register(CourseRunGrade, CourseRunGradeAdmin)
admin.site.register(CourseRunGradeAudit, CourseRunGradeAuditAdmin)
admin.site.register(CourseRunCertificate, CourseRunCertificateAdmin)
admin.site.register(ProgramCertificate, ProgramCertificateAdmin)
