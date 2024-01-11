"""Admin classes for affiliate models"""

from django.contrib import admin

from affiliate.models import Affiliate, AffiliateReferralAction
from mitxpro.admin import TimestampedModelAdmin


@admin.register(Affiliate)
class AffiliateAdmin(TimestampedModelAdmin):
    """Admin for Affiliate"""

    model = Affiliate
    list_display = ["id", "code", "name"]


@admin.register(AffiliateReferralAction)
class AffiliateReferralActionAdmin(TimestampedModelAdmin):
    """Admin for AffiliateReferralAction"""

    model = AffiliateReferralAction
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

    def get_queryset(self, request):  # noqa: ARG002
        """Overrides base method"""  # noqa: D401
        return self.model.objects.select_related("affiliate")

    @admin.display(
        description="Affiliate Name",
        ordering="affiliate__name",
    )
    def get_affiliate_name(self, obj):
        """Returns the related Affiliate name"""  # noqa: D401
        return obj.affiliate.name

    @admin.display(
        description="Affiliate Code",
        ordering="affiliate__code",
    )
    def get_affiliate_code(self, obj):
        """Returns the related Affiliate code"""  # noqa: D401
        return obj.affiliate.code
