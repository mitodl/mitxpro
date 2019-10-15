"""
Admin site bindings for sheets models
"""

from django.contrib import admin

from sheets import models


class CouponGenerationRequestAdmin(admin.ModelAdmin):
    """Admin for CouponGenerationRequest"""

    model = models.CouponGenerationRequest
    list_display = ("id", "transaction_id", "completed", "spreadsheet_updated")


class GoogleApiAuthAdmin(admin.ModelAdmin):
    """Admin for GoogleApiAuth"""

    model = models.GoogleApiAuth
    list_display = ("id", "user")


admin.site.register(models.CouponGenerationRequest, CouponGenerationRequestAdmin)
admin.site.register(models.GoogleApiAuth, GoogleApiAuthAdmin)
