""" ecommerce serializers """
from rest_framework import serializers

from courses.models import Course
from courses.serializers import CourseRunSerializer
from ecommerce import models
from ecommerce.api import latest_product_version, latest_coupon_version


class ProductVersionSerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for viewing/updating items in basket """

    type = serializers.SerializerMethodField()
    course_runs = serializers.SerializerMethodField()

    def get_type(self, instance):
        """ Return the product version type """
        return instance.product.content_type.model

    def get_course_runs(self, instance):
        """ Return the course runs in the product """
        course_runs = []
        if instance.product.content_type.model == "courserun":
            course_runs.append(instance.product.content_object)
        elif instance.product.content_type.model == "course":
            course_runs.append(instance.product.content_object.first_unexpired_run)
        elif instance.product.content_type.model == "program":
            for course in Course.objects.filter(
                program=instance.product.content_object
            ):
                course_runs.append(course.first_unexpired_run)
        return [
            CourseRunSerializer(instance=course_run).data for course_run in course_runs
        ]

    class Meta:
        fields = ["id", "price", "description", "type", "course_runs"]
        model = models.ProductVersion


class CouponSelectionSerializer(serializers.ModelSerializer):
    """CouponSelection serializer for viewing/updating coupons in basket"""

    code = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    targets = serializers.SerializerMethodField()

    def get_code(self, instance):
        """ Get the coupon code"""
        return instance.coupon.coupon_code

    def get_amount(self, instance):
        """ Get the coupon discount amount """
        return latest_coupon_version(instance.coupon).invoice_version.amount

    def get_targets(self, instance):
        """ Get the product version id(s) in the basket the coupon applies to"""
        eligible_product_ids = (
            models.CouponEligibility.objects.select_related("coupon", "product")
            .filter(
                coupon__coupon_code=instance.coupon.coupon_code,
                coupon__enabled=True,
                product__in=instance.basket.basketitems.values_list(
                    "product", flat=True
                ),
            )
            .values_list("product", flat=True)
        )
        return [
            latest_product_version(product).id
            for product in models.Product.objects.filter(id__in=eligible_product_ids)
        ]

    class Meta:
        fields = ["code", "amount", "targets"]
        model = models.CouponSelection


class BasketSerializer(serializers.ModelSerializer):
    """Basket model serializer"""

    items = serializers.SerializerMethodField()
    coupons = serializers.SerializerMethodField()

    def get_items(self, instance):
        """ Get the basket items """
        return [
            ProductVersionSerializer(instance=latest_product_version(item.product)).data
            for item in instance.basketitems.all()
        ]

    def get_coupons(self, instance):
        """ Get the basket coupons """
        return [
            CouponSelectionSerializer(instance=coupon_selection).data
            for coupon_selection in models.CouponSelection.objects.filter(
                basket=instance
            )
        ]

    class Meta:
        fields = ["items", "coupons"]
        model = models.Basket
