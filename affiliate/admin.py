"""Admin classes for affiliate models"""

from django.contrib import admin

from affiliate import models
from mitxpro.admin import TimestampedModelAdmin


class AffiliateAdmin(TimestampedModelAdmin):
    """Admin for Affiliate"""

    model = models.Affiliate
    list_display = ["id", "code", "name"]


class AffiliateReferralActionAdmin(TimestampedModelAdmin):
    """Admin for AffiliateReferralAction"""

    model = models.AffiliateReferralAction
    include_created_on_in_list = True
    list_display = [
        "id",
        "get_affiliate_name",
        "get_affiliate_code",
        "created_user_id",
        "created_order_id",
    ]
    raw_id_fields = ["affiliate", "created_user", "created_order"]
    list_filter = ["affiliate__name"]
    ordering = ["-created_on"]

    def get_queryset(self, request):
        """Overrides base method"""
        return self.model.objects.select_related("affiliate")

    def get_affiliate_name(self, obj):
        """Returns the related Affiliate name"""
        return obj.affiliate.name

    get_affiliate_name.short_description = "Affiliate Name"
    get_affiliate_name.admin_order_field = "affiliate__name"

    def get_affiliate_code(self, obj):
        """Returns the related Affiliate code"""
        return obj.affiliate.code

    get_affiliate_name.short_description = "Affiliate Code"
    get_affiliate_name.admin_order_field = "affiliate__code"


admin.site.register(models.Affiliate, AffiliateAdmin)
admin.site.register(models.AffiliateReferralAction, AffiliateReferralActionAdmin)
