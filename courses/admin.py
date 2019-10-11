"""
Admin site bindings for profiles
"""

from django.contrib import admin

from mitxpro.utils import get_field_names
from mitxpro.admin import AuditableModelAdmin
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
    CourseTopic,
    ProgramCertificate,
)


class ProgramAdmin(admin.ModelAdmin):
    """Admin for Program"""

    model = Program
    search_fields = ["title", "readable_id"]
    list_display = ("id", "title", "readable_id")
    list_filter = ["live"]


class CourseAdmin(admin.ModelAdmin):
    """Admin for Course"""

    model = Course
    search_fields = ["title", "topics__name"]
    list_filter = ["live", "program", "topics"]


class CourseRunAdmin(admin.ModelAdmin):
    """Admin for CourseRun"""

    model = CourseRun
    search_fields = ["title", "courseware_id"]
    list_display = ("id", "title", "courseware_id")
    list_filter = ["live", "course"]


class ProgramEnrollmentAdmin(AuditableModelAdmin):
    """Admin for ProgramEnrollment"""

    model = ProgramEnrollment
    search_fields = [
        "user__email",
        "user__username",
        "company__name",
        "program__readable_id",
        "program__title",
    ]
    list_filter = ["active", "change_status"]
    list_display = ("id", "get_user_email", "get_program_readable_id", "change_status")
    raw_id_fields = ("user", "order", "program")

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
        return qs.select_related("user", "program")

    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    get_user_email.short_description = "User Email"
    get_user_email.admin_order_field = "user__email"

    def get_program_readable_id(self, obj):
        """Returns the related Program readable_id"""
        return obj.program.readable_id

    get_program_readable_id.short_description = "Program"
    get_program_readable_id.admin_order_field = "program__readable_id"


class ProgramEnrollmentAuditAdmin(admin.ModelAdmin):
    """Admin for ProgramEnrollmentAudit"""

    model = ProgramEnrollmentAudit
    readonly_fields = get_field_names(ProgramEnrollmentAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunEnrollmentAdmin(AuditableModelAdmin):
    """Admin for CourseRunEnrollment"""

    model = CourseRunEnrollment
    search_fields = [
        "user__email",
        "user__username",
        "company__name",
        "run__courseware_id",
        "run__title",
    ]
    list_filter = ["active", "change_status", "edx_enrolled"]
    list_display = ("id", "get_user_email", "get_run_courseware_id", "change_status")
    raw_id_fields = ("user", "order", "run")

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
        return qs.select_related("user", "run")

    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    get_user_email.short_description = "User Email"
    get_user_email.admin_order_field = "user__email"

    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.run.courseware_id

    get_run_courseware_id.short_description = "Course Run"
    get_run_courseware_id.admin_order_field = "run__courseware_id"


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
    list_display = ["id", "get_user_email", "get_run_courseware_id", "grade"]
    list_filter = ["passed", "set_by_admin", "course_run"]
    raw_id_fields = ("user",)

    def get_queryset(self, request):
        return self.model.objects.get_queryset().select_related("user", "course_run")

    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    get_user_email.short_description = "User Email"
    get_user_email.admin_order_field = "user__email"

    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.course_run.courseware_id

    get_run_courseware_id.short_description = "Course Run"
    get_run_courseware_id.admin_order_field = "course_run__courseware_id"


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
    raw_id_fields = ("user",)

    def get_queryset(self, request):
        return self.model.objects.get_queryset().select_related("user", "course_run")


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
    raw_id_fields = ("user",)

    def get_queryset(self, request):
        return self.model.objects.get_queryset().select_related("user", "program")


class CourseTopicAdmin(admin.ModelAdmin):
    """Admin for CourseTopic"""

    model = CourseTopic


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
admin.site.register(CourseTopic, CourseTopicAdmin)
