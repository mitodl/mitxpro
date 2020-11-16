"""
Admin site bindings for sheets models
"""

from django.contrib import admin
from django.core.exceptions import ValidationError

from mitxpro.admin import SingletonModelAdmin
from sheets import models


class CouponGenerationRequestAdmin(admin.ModelAdmin):
    """Admin for CouponGenerationRequest"""

    model = models.CouponGenerationRequest
    list_display = ("id", "purchase_order_id", "coupon_name", "date_completed")


class RefundRequestAdmin(admin.ModelAdmin):
    """Admin for RefundRequest"""

    model = models.RefundRequest
    list_display = ("id", "form_response_id", "date_completed")


class DeferralRequestAdmin(admin.ModelAdmin):
    """Admin for DeferralRequest"""

    model = models.DeferralRequest
    list_display = ("id", "form_response_id", "date_completed")


class GoogleApiAuthAdmin(SingletonModelAdmin):
    """Admin for GoogleApiAuth"""

    model = models.GoogleApiAuth
    list_display = ("id", "requesting_user")


class GoogleFileWatchAdmin(admin.ModelAdmin):
    """Admin for GoogleFileWatch"""

    model = models.GoogleFileWatch
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


class FileWatchRenewalAttemptAdmin(admin.ModelAdmin):
    """Admin for FileWatchRenewalAttempt"""

    model = models.FileWatchRenewalAttempt
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


admin.site.register(models.CouponGenerationRequest, CouponGenerationRequestAdmin)
admin.site.register(models.RefundRequest, RefundRequestAdmin)
admin.site.register(models.DeferralRequest, DeferralRequestAdmin)
admin.site.register(models.GoogleApiAuth, GoogleApiAuthAdmin)
admin.site.register(models.GoogleFileWatch, GoogleFileWatchAdmin)
admin.site.register(models.FileWatchRenewalAttempt, FileWatchRenewalAttemptAdmin)
