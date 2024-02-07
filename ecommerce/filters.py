"""Ecommerce filters"""
from django.core.exceptions import ValidationError
from django_filters import rest_framework as filters

from courses.constants import VALID_PRODUCT_TYPE_CHOICES
from ecommerce.models import Product, Coupon


class ProductFilter(filters.FilterSet):
    """Filters for Product model"""

    product_type = filters.ChoiceFilter(
        field_name="content_type__model", choices=VALID_PRODUCT_TYPE_CHOICES
    )

    class Meta:
        model = Product
        fields = []


class CouponUtils:
    @staticmethod
    def validate_unique_coupon_code(value):
        """
        Validator function to check the uniqueness of coupon codes across Coupon and B2BCoupon models.
        """
        if CouponUtils.is_coupon_code_exists(value):
            raise ValidationError("Coupon code already exists in the plaform.")

    @staticmethod
    def is_coupon_code_exists(value):
        """
        Checks if the coupon code exists in either Coupon or B2BCoupon models.
        """
        from b2b_ecommerce.models import B2BCoupon

        return (
            Coupon.objects.filter(coupon_code=value).exists()
            or B2BCoupon.objects.filter(coupon_code=value).exists()
        )

    @staticmethod
    def is_coupon_code_unique(value):
        """
        Checks if the coupon code is unique across Coupon and B2BCoupon models.
        """
        return not CouponUtils.is_coupon_code_exists(value)
