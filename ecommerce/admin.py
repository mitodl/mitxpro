"""admin classes for ecommerce"""
from django.contrib import admin

from ecommerce.models import (
    Line,
    Order,
    OrderAudit,
    Receipt,
    Coupon,
    CouponVersion,
    CouponInvoiceVersion,
    CouponInvoice,
    CouponSelection,
    CouponEligibility,
    CouponRedemption,
)
from mitxpro.utils import get_field_names


class LineAdmin(admin.ModelAdmin):
    """Admin for Line"""

    model = Line

    readonly_fields = get_field_names(Line)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OrderAdmin(admin.ModelAdmin):
    """Admin for Order"""

    model = Order
    list_filter = ("status",)
    list_display = ("id", "purchaser", "status", "created_on")
    search_fields = ("purchaser__username", "purchaser__email")

    readonly_fields = [name for name in get_field_names(Order) if name != "status"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """
        Saves object and logs change to object
        """
        obj.save_and_log(request.user)


class OrderAuditAdmin(admin.ModelAdmin):
    """Admin for OrderAudit"""

    model = OrderAudit
    readonly_fields = get_field_names(OrderAudit)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReceiptAdmin(admin.ModelAdmin):
    """Admin for Receipt"""

    model = Receipt
    readonly_fields = get_field_names(Receipt)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CouponInvoiceVersionInline(admin.StackedInline):
    """Admin Inline for CouponInvoiceVersion objects"""

    model = CouponInvoiceVersion
    extra = 1
    show_change_link = True


class CouponVersionInline(admin.StackedInline):
    """Admin Inline for CouponVersion objects"""

    model = CouponVersion
    extra = 1
    show_change_link = True


class CouponAdmin(admin.ModelAdmin):
    """Admin for Coupons"""

    model = Coupon
    inlines = [CouponVersionInline]


class CouponInvoiceAdmin(admin.ModelAdmin):
    """Admin for CouponInvoices"""

    model = CouponInvoice
    inlines = [CouponInvoiceVersionInline]


class CouponInvoiceVersionAdmin(admin.ModelAdmin):
    """Admin for CouponInvoiceVersions"""

    model = CouponInvoiceVersion


class CouponVersionAdmin(admin.ModelAdmin):
    """Admin for CouponVersions"""

    model = CouponVersion


class CouponSelectionAdmin(admin.ModelAdmin):
    """Admin for CouponSelections"""

    model = CouponSelection


class CouponEligibilityAdmin(admin.ModelAdmin):
    """Admin for CouponEligibilitys"""

    model = CouponEligibility


class CouponRedemptionAdmin(admin.ModelAdmin):
    """Admin for CouponRedemptions"""

    model = CouponRedemption


admin.site.register(Line, LineAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderAudit, OrderAuditAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponVersion, CouponVersionAdmin)
admin.site.register(CouponInvoice, CouponInvoiceAdmin)
admin.site.register(CouponInvoiceVersion, CouponInvoiceVersionAdmin)
admin.site.register(CouponSelection, CouponSelectionAdmin)
admin.site.register(CouponEligibility, CouponEligibilityAdmin)
admin.site.register(CouponRedemption, CouponRedemptionAdmin)
