"""
Admin bindings for voucher
"""
from django.contrib import admin

from voucher.models import Voucher


class VoucherAdmin(admin.ModelAdmin):
    """Admin view for vouchers"""

    list_display = (
        "id",
        "course_id_input",
        "course_title_input",
        "course_start_date_input",
        "employee_name",
    )
    search_fields = (
        "user__username",
        "user__email",
        "product__id",
        "employee_name",
        "course_id_input",
        "course_title_input",
    )
    readonly_fields = ("coupon", "product", "enrollment")


admin.site.register(Voucher, VoucherAdmin)
