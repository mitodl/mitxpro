"""
Admin site bindings for sheets models
"""

from django.contrib import admin

from sheets import models


class CouponGenerationRequestAdmin(admin.ModelAdmin):
    """Admin for CouponGenerationRequest"""

    model = models.CouponGenerationRequest
    list_display = ("id", "purchase_order_id", "completed")


class GoogleApiAuthAdmin(admin.ModelAdmin):
    """Admin for GoogleApiAuth"""

    model = models.GoogleApiAuth
    list_display = ("id", "requesting_user")

    def has_add_permission(self, request):
        """Overridden method - prevent adding a GoogleApiAuth if one already exists"""
        return models.GoogleApiAuth.objects.count() == 0


admin.site.register(models.CouponGenerationRequest, CouponGenerationRequestAdmin)
admin.site.register(models.GoogleApiAuth, GoogleApiAuthAdmin)
