"""Admin interface for B2B ecommerce"""

from django.contrib import admin

from b2b_ecommerce.models import B2BCoupon, B2BCouponRedemption, B2BOrder, B2BReceipt
from mitxpro.admin import AuditableModelAdmin


class B2BCouponAdmin(AuditableModelAdmin):
    """Admin for B2BCoupon"""

    model = B2BCoupon


class B2BCouponRedemptionAdmin(admin.ModelAdmin):
    """Admin for B2BCouponRedemption"""

    model = B2BCouponRedemption


class B2BReceiptAdmin(admin.ModelAdmin):
    """Admin for B2BReceipt"""

    model = B2BReceipt


class B2BOrderAdmin(AuditableModelAdmin):
    """Admin for B2BOrder"""

    model = B2BOrder


admin.site.register(B2BReceipt, B2BReceiptAdmin)
admin.site.register(B2BCoupon, B2BCouponAdmin)
admin.site.register(B2BOrder, B2BOrderAdmin)
admin.site.register(B2BCouponRedemption, B2BCouponRedemptionAdmin)
