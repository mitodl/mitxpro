"""
Admin site bindings for profiles
"""

from django.contrib import admin
from django.db import models
from django.forms import TextInput

from mitxpro.admin import AuditableModelAdmin, TimestampedModelAdmin
from mitxpro.utils import get_field_names

from .models import (
    Course,
    CourseRun,
    CourseRunCertificate,
    CourseRunEnrollment,
    CourseRunEnrollmentAudit,
    CourseRunGrade,
    CourseRunGradeAudit,
    Platform,
    Program,
    ProgramCertificate,
    ProgramEnrollment,
    ProgramEnrollmentAudit,
    ProgramRun,
)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    """Admin for Program"""

    model = Program
    search_fields = ["title", "readable_id", "platform__name"]
    list_display = ("id", "title", "readable_id", "platform")
    list_filter = ["live", "platform"]


@admin.register(ProgramRun)
class ProgramRunAdmin(admin.ModelAdmin):
    """Admin for ProgramRun"""

    model = ProgramRun
    list_display = ("id", "program", "run_tag", "full_readable_id")
    list_filter = ["program"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin for Course"""

    model = Course
    search_fields = ["title", "readable_id", "platform__name"]
    list_display = ("id", "title", "get_program", "position_in_program", "platform")
    list_filter = ["live", "program", "platform"]
    formfield_overrides = {
        models.CharField: {"widget": TextInput(attrs={"size": "80"})}
    }

    @admin.display(
        description="Program",
        ordering="program__readable_id",
    )
    def get_program(self, obj):
        """Returns the related User email"""
        return obj.program.readable_id if obj.program is not None else None


@admin.register(CourseRun)
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


@admin.register(ProgramEnrollment)
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

    @admin.display(
        description="User Email",
        ordering="user__email",
    )
    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    @admin.display(
        description="Program",
        ordering="program__readable_id",
    )
    def get_program_readable_id(self, obj):
        """Returns the related Program readable_id"""
        return obj.program.readable_id


@admin.register(ProgramEnrollmentAudit)
class ProgramEnrollmentAuditAdmin(TimestampedModelAdmin):
    """Admin for ProgramEnrollmentAudit"""

    model = ProgramEnrollmentAudit
    include_created_on_in_list = True
    list_display = ("id", "enrollment_id", "get_program_readable_id", "get_user")
    readonly_fields = get_field_names(ProgramEnrollmentAudit)

    @admin.display(
        description="Program",
        ordering="enrollment__program__readable_id",
    )
    def get_program_readable_id(self, obj):
        """Returns the related Program readable_id"""
        return obj.enrollment.program.readable_id

    @admin.display(
        description="User",
        ordering="enrollment__user__email",
    )
    def get_user(self, obj):
        """Returns the related User's email"""
        return obj.enrollment.user.email

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseRunEnrollment)
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

    @admin.display(
        description="User Email",
        ordering="user__email",
    )
    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    @admin.display(
        description="Course Run",
        ordering="run__courseware_id",
    )
    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.run.courseware_id


@admin.register(CourseRunEnrollmentAudit)
class CourseRunEnrollmentAuditAdmin(TimestampedModelAdmin):
    """Admin for CourseRunEnrollmentAudit"""

    model = CourseRunEnrollmentAudit
    include_created_on_in_list = True
    list_display = ("id", "enrollment_id", "get_run_courseware_id", "get_user")
    readonly_fields = get_field_names(CourseRunEnrollmentAudit)

    @admin.display(
        description="Course Run",
        ordering="enrollment__run__courseware_id",
    )
    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.enrollment.run.courseware_id

    @admin.display(
        description="User",
        ordering="enrollment__user__email",
    )
    def get_user(self, obj):
        """Returns the related User's email"""
        return obj.enrollment.user.email

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseRunGrade)
class CourseRunGradeAdmin(admin.ModelAdmin):
    """Admin for CourseRunGrade"""

    model = CourseRunGrade
    list_display = ["id", "get_user_email", "get_run_courseware_id", "grade"]
    list_filter = ["passed", "set_by_admin", "course_run__courseware_id"]
    raw_id_fields = ("user",)
    search_fields = ["user__email", "user__username"]

    def get_queryset(self, request):
        return self.model.objects.get_queryset().select_related("user", "course_run")

    @admin.display(
        description="User Email",
        ordering="user__email",
    )
    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.user.email

    @admin.display(
        description="Course Run",
        ordering="course_run__courseware_id",
    )
    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.course_run.courseware_id


@admin.register(CourseRunGradeAudit)
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

    @admin.display(
        description="User Email",
        ordering="course_run_grade__user__email",
    )
    def get_user_email(self, obj):
        """Returns the related User email"""
        return obj.course_run_grade.user.email

    @admin.display(
        description="Course Run",
        ordering="course_run_grade__course_run__courseware_id",
    )
    def get_run_courseware_id(self, obj):
        """Returns the related CourseRun courseware_id"""
        return obj.course_run_grade.course_run.courseware_id

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CourseRunCertificate)
class CourseRunCertificateAdmin(TimestampedModelAdmin):
    """Admin for CourseRunCertificate"""

    model = CourseRunCertificate
    include_timestamps_in_list = True
    list_display = [
        "uuid",
        "user",
        "course_run",
        "get_revoked_state",
        "certificate_page_revision",
    ]
    search_fields = [
        "course_run__courseware_id",
        "course_run__title",
        "user__username",
        "user__email",
    ]
    raw_id_fields = ("user",)

    @admin.display(
        description="Active",
        boolean=True,
    )
    def get_revoked_state(self, obj):
        """return the revoked state"""
        return obj.is_revoked is not True

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related(
            "user", "course_run"
        )


@admin.register(ProgramCertificate)
class ProgramCertificateAdmin(TimestampedModelAdmin):
    """Admin for ProgramCertificate"""

    model = ProgramCertificate
    include_timestamps_in_list = True
    list_display = [
        "uuid",
        "user",
        "program",
        "get_revoked_state",
        "certificate_page_revision",
    ]
    search_fields = [
        "program__readable_id",
        "program__title",
        "user__username",
        "user__email",
    ]
    raw_id_fields = ("user",)

    @admin.display(
        description="Active",
        boolean=True,
    )
    def get_revoked_state(self, obj):
        """return the revoked state"""
        return obj.is_revoked is not True

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset().select_related("user", "program")


@admin.register(Platform)
class PlatformAdmin(TimestampedModelAdmin):
    """Admin for Platform"""

    model = Platform
    list_display = ["id", "name", "created_on", "updated_on"]
    search_fields = ["name"]
