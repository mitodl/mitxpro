"""
Admin site bindings for profiles
"""

from django.contrib import admin
from django.db import models
from django.forms import TextInput


from mitxpro.utils import get_field_names
from mitxpro.admin import AuditableModelAdmin, TimestampedModelAdmin
from .models import (
    Program,
    ProgramRun,
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


class ProgramRunAdmin(admin.ModelAdmin):
    """Admin for ProgramRun"""

    model = ProgramRun
    list_display = ("id", "program", "run_tag", "full_readable_id")
    list_filter = ["program"]


class CourseAdmin(admin.ModelAdmin):
    """Admin for Course"""

    model = Course
    search_fields = ["title", "topics__name", "readable_id"]
    list_display = ("id", "title", "get_program", "position_in_program")
    list_filter = ["live", "program", "topics"]

    formfield_overrides = {
        models.CharField: {"widget": TextInput(attrs={"size": "80"})}
    }

    def get_program(self, obj):
        """Returns the related User email"""
        return obj.program.readable_id if obj.program is not None else None

    get_program.short_description = "Program"
    get_program.admin_order_field = "program__readable_id"


class CourseRunAdmin(TimestampedModelAdmin):
    """Admin for CourseRun"""

    model = CourseRun
    search_fields = ["title", "courseware_id"]
    list_display = (
        "id",
        "title",
        "courseware_id",
        "run_tag",
        "start_date",
        "end_date",
        "enrollment_start",
    )
    list_filter = ["live", "course"]

    formfield_overrides = {
        models.CharField: {"widget": TextInput(attrs={"size": "80"})}
    }


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


class ProgramEnrollmentAuditAdmin(TimestampedModelAdmin):
    """Admin for ProgramEnrollmentAudit"""

    model = ProgramEnrollmentAudit
    include_created_on_in_list = True
    list_display = ("id", "enrollment_id", "get_program_readable_id", "get_user")
    readonly_fields = get_field_names(ProgramEnrollmentAudit)

    def get_program_readable_id(self, obj):
        """Returns the related Program readable_id"""
        return obj.enrollment.program.readable_id

    get_program_readable_id.short_description = "Program"
    get_program_readable_id.admin_order_field = "enrollment__program__readable_id"

    def get_user(self, obj):
        """Returns the related User's email"""
        return obj.enrollment.user.email

    get_user.short_description = "User"
    get_user.admin_order_field = "enrollment__user__email"

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


class CourseRunEnrollmentAuditAdmin(TimestampedModelAdmin):
    """Admin for CourseRunEnrollmentAudit"""

    model = CourseRunEnrollmentAudit
    include_created_on_in_list = True
    list_display = ("id", "enrollment_id", "get_run_courseware_id", "get_user")
    readonly_fields = get_field_names(CourseRunEnrollmentAudit)

    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.enrollment.run.courseware_id

    get_run_courseware_id.short_description = "Course Run"
    get_run_courseware_id.admin_order_field = "enrollment__run__courseware_id"

    def get_user(self, obj):
        """Returns the related User's email"""
        return obj.enrollment.user.email

    get_user.short_description = "User"
    get_user.admin_order_field = "enrollment__user__email"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunGradeAdmin(admin.ModelAdmin):
    """Admin for CourseRunGrade"""

    model = CourseRunGrade
    list_display = ["id", "get_user_email", "get_run_courseware_id", "grade"]
    list_filter = ["passed", "set_by_admin", "course_run__courseware_id"]
    raw_id_fields = ("user",)
    search_fields = ["user__email", "user__username"]

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


class CourseRunGradeAuditAdmin(TimestampedModelAdmin):
    """Admin for CourseRunGradeAudit"""

    model = CourseRunGradeAudit
    include_created_on_in_list = True
    list_display = (
        "id",
        "course_run_grade_id",
        "get_user_email",
        "get_run_courseware_id",
    )
    readonly_fields = get_field_names(CourseRunGradeAudit)

    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.course_run_grade.user.email

    get_user_email.short_description = "User Email"
    get_user_email.admin_order_field = "course_run_grade__user__email"

    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.course_run_grade.course_run.courseware_id

    get_run_courseware_id.short_description = "Course Run"
    get_run_courseware_id.admin_order_field = (
        "course_run_grade__course_run__courseware_id"
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRunCertificateAdmin(TimestampedModelAdmin):
    """Admin for CourseRunCertificate"""

    model = CourseRunCertificate
    include_timestamps_in_list = True
    list_display = ["uuid", "user", "course_run", "get_revoked_state"]
    search_fields = [
        "course_run__courseware_id",
        "course_run__title",
        "user__username",
        "user__email",
    ]
    raw_id_fields = ("user",)

    def get_revoked_state(self, obj):
        """ return the revoked state"""
        return obj.is_revoked is not True

    get_revoked_state.short_description = "Active"
    get_revoked_state.boolean = True

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related(
            "user", "course_run"
        )


class ProgramCertificateAdmin(TimestampedModelAdmin):
    """Admin for ProgramCertificate"""

    model = ProgramCertificate
    include_timestamps_in_list = True
    list_display = ["uuid", "user", "program", "get_revoked_state"]
    search_fields = [
        "program__readable_id",
        "program__title",
        "user__username",
        "user__email",
    ]
    raw_id_fields = ("user",)

    def get_revoked_state(self, obj):
        """ return the revoked state"""
        return obj.is_revoked is not True

    get_revoked_state.short_description = "Active"
    get_revoked_state.boolean = True

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related("user", "program")


class CourseTopicAdmin(admin.ModelAdmin):
    """Admin for CourseTopic"""

    model = CourseTopic


admin.site.register(Program, ProgramAdmin)
admin.site.register(ProgramRun, ProgramRunAdmin)
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
