"""
Admin site bindings for sheets models
"""

from django.contrib import admin
from django.core.exceptions import ValidationError

from mitxpro.admin import SingletonModelAdmin
from sheets.models import (
    CouponGenerationRequest,
    RefundRequest,
    DeferralRequest,
    GoogleApiAuth,
    GoogleFileWatch,
    FileWatchRenewalAttempt,
)


@admin.register(CouponGenerationRequest)
class CouponGenerationRequestAdmin(admin.ModelAdmin):
    """Admin for CouponGenerationRequest"""

    model = CouponGenerationRequest
    list_display = ("id", "purchase_order_id", "coupon_name", "date_completed")


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    """Admin for RefundRequest"""

    model = RefundRequest
    list_display = ("id", "form_response_id", "date_completed")


@admin.register(DeferralRequest)
class DeferralRequestAdmin(admin.ModelAdmin):
    """Admin for DeferralRequest"""

    model = DeferralRequest
    list_display = ("id", "form_response_id", "date_completed")


@admin.register(GoogleApiAuth)
class GoogleApiAuthAdmin(SingletonModelAdmin):
    """Admin for GoogleApiAuth"""

    model = GoogleApiAuth
    list_display = ("id", "requesting_user")


@admin.register(GoogleFileWatch)
class GoogleFileWatchAdmin(admin.ModelAdmin):
    """Admin for GoogleFileWatch"""

    model = GoogleFileWatch
    list_display = (
        "id",
        "file_id",
        "channel_id",
        "activation_date",
        "expiration_date",
        "last_request_received",
    )
    ordering = ["-expiration_date"]

    def save_form(self, request, form, change):
        if not change:
            file_id = form.cleaned_data["file_id"]
            if self.model.objects.filter(file_id=file_id).exists():
                raise ValidationError(
                    "Only one GoogleFileWatch object should exist for each unique file_id (file_id provided: {}). "
                    "Update the existing object instead of creating a new one.".format(
                        file_id
                    )
                )
        return super().save_form(request, form, change)


@admin.register(FileWatchRenewalAttempt)
class FileWatchRenewalAttemptAdmin(admin.ModelAdmin):
    """Admin for FileWatchRenewalAttempt"""

    model = FileWatchRenewalAttempt
    list_display = (
        "id",
        "sheet_type",
        "sheet_file_id",
        "date_attempted",
        "result",
        "result_status_code",
    )
    search_fields = ("sheet_file_id", "result")
    list_filter = ("sheet_type", "result_status_code")
    readonly_fields = ("date_attempted",)
    ordering = ("-date_attempted",)
