"""
Admin site bindings for compliance
"""

import pycountry
from django.conf import settings
from django.contrib import admin

from mitxpro.utils import get_field_names
from users.utils import ensure_active_user

from .constants import RESULT_MANUALLY_APPROVED, RESULT_SUCCESS
from .models import ExportsInquiryLog


@admin.register(ExportsInquiryLog)
class ExportsInquiryLogAdmin(admin.ModelAdmin):
    """Admin for ExportsInquiryLog"""

    model = ExportsInquiryLog
    search_fields = ["user__email", "computed_result", "info_code", "reason_code"]
    list_filter = [
        "computed_result",
        "info_code",
        "reason_code",
        "user__legal_address__country",
    ]
    list_display = ["user", "computed_result", "info_code", "reason_code", "country"]
    list_select_related = ["user__legal_address"]
    readonly_fields = [] if settings.DEBUG else get_field_names(ExportsInquiryLog)
    actions = ["manually_approve_inquiry"]

    def country(self, instance):
        """Get country name from ISO Alpha-2 country code"""
        country = pycountry.countries.get(alpha_2=instance.user.legal_address.country)
        return country.name if country else "N/A"

    @admin.action(description="Manually approve selected records")
    def manually_approve_inquiry(self, request, queryset):  # noqa: ARG002
        """Admin action to manually approve export compliance inquiry records"""
        eligible_objects = queryset.exclude(
            computed_result__in=[RESULT_MANUALLY_APPROVED, RESULT_SUCCESS]
        )
        for obj in eligible_objects:
            ensure_active_user(obj.user)
        eligible_objects.update(computed_result=RESULT_MANUALLY_APPROVED)

    def has_add_permission(self, request):  # noqa: ARG002
        # We want to allow this while debugging
        return settings.DEBUG

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        # We want to allow this while debugging
        return settings.DEBUG
