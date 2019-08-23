"""Admin interface for B2B ecommerce"""

from django.contrib import admin

from b2b_ecommerce.models import B2BCoupon, B2BCouponRedemption, B2BOrder


class B2BCouponAdmin(admin.ModelAdmin):
    """Admin for B2BCoupon"""

    model = B2BCoupon

    def save_model(self, request, obj, form, change):
        """
        Override to save and log object
        """
        return obj.save_and_log(request.user)


class B2BCouponRedemptionAdmin(admin.ModelAdmin):
    """Admin for B2BCouponRedemption"""

    model = B2BCouponRedemption


class B2BOrderAdmin(admin.ModelAdmin):
    """Admin for B2BOrder"""

    model = B2BOrder

    def save_model(self, request, obj, form, change):
        """
        Override to save and log object
        """
        return obj.save_and_log(request.user)


admin.site.register(B2BCoupon, B2BCouponAdmin)
admin.site.register(B2BOrder, B2BOrderAdmin)
admin.site.register(B2BCouponRedemption, B2BCouponRedemptionAdmin)
