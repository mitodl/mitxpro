"""
Voucher Models
"""
from django.conf import settings
from django.db import models

from ecommerce.models import CouponRedemption, CouponVersion
from mitxpro.models import TimestampedModel
from voucher.utils import voucher_upload_path


class Voucher(TimestampedModel):
    """
    Voucher stores values parsed from a raw PDF as well as mid-enrollment process information such as
    an attached coupon and a selected product (course_run)
    """

    voucher_id = models.CharField(max_length=32, null=True, blank=True)
    employee_id = models.CharField(max_length=32)
    employee_name = models.CharField(max_length=128)
    course_start_date_input = models.DateField()
    course_id_input = models.CharField(max_length=255)
    course_title_input = models.CharField(max_length=255)
    pdf = models.FileField(upload_to=voucher_upload_path, null=True)
    uploaded = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vouchers"
    )

    coupon = models.OneToOneField(
        "ecommerce.Coupon", on_delete=models.SET_NULL, null=True, related_name="voucher"
    )
    product = models.ForeignKey(
        "ecommerce.Product", on_delete=models.SET_NULL, null=True
    )
    enrollment = models.OneToOneField(
        "courses.CourseRunEnrollment",
        on_delete=models.SET_NULL,
        null=True,
        related_name="voucher",
    )

    def is_redeemed(self):
        """Return True if a voucher has a coupon attached and a CouponRedemption object exists for that coupon"""
        return (
            self.coupon is not None
            and CouponRedemption.objects.filter(
                coupon_version=CouponVersion.objects.filter(coupon=self.coupon).last()
            ).first()
            is not None
        )
