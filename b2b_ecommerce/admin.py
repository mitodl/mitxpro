"""Admin interface for B2B ecommerce"""

from django.contrib import admin

from b2b_ecommerce.models import B2BCoupon, B2BCouponRedemption, B2BOrder, B2BReceipt
from mitxpro.admin import AuditableModelAdmin


@admin.register(B2BCoupon)
class B2BCouponAdmin(AuditableModelAdmin):
    """Admin for B2BCoupon"""

    model = B2BCoupon


@admin.register(B2BCouponRedemption)
class B2BCouponRedemptionAdmin(admin.ModelAdmin):
    """Admin for B2BCouponRedemption"""

    model = B2BCouponRedemption


@admin.register(B2BReceipt)
class B2BReceiptAdmin(admin.ModelAdmin):
    """Admin for B2BReceipt"""

    model = B2BReceipt


@admin.register(B2BOrder)
class B2BOrderAdmin(AuditableModelAdmin):
    """Admin for B2BOrder"""

    model = B2BOrder
