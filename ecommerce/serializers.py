""" ecommerce serializers """
from uuid import uuid4

from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from courses.models import Course, CourseRun
from courses.serializers import CourseRunSerializer
from courses.constants import DEFAULT_COURSE_IMG_PATH
from ecommerce import models
from ecommerce.api import latest_product_version, latest_coupon_version
from ecommerce.models import (
    CouponPaymentVersion,
    CouponPayment,
    Coupon,
    Product,
    Company,
    CouponVersion,
    CouponEligibility,
)


class ProductSerializer(serializers.ModelSerializer):
    """ Product Serializer """

    title = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()

    def get_title(self, instance):
        """ Return the product title """
        return instance.content_type.get_object_for_this_type(
            pk=instance.object_id
        ).title

    def get_product_type(self, instance):
        """ Return the product type """
        return instance.content_type.model

    class Meta:
        fields = "__all__"
        model = models.Product


class ProductVersionSerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for viewing/updating items in basket """

    type = serializers.SerializerMethodField()
    course_runs = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

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

    def get_thumbnail_url(self, instance):
        """Return the thumbnail for the course or program"""
        content_object = instance.product.content_object
        if isinstance(content_object, CourseRun):
            catalog_image_url = content_object.course.catalog_image_url
        else:
            catalog_image_url = content_object.catalog_image_url
        return catalog_image_url or static(DEFAULT_COURSE_IMG_PATH)

    class Meta:
        fields = ["id", "price", "description", "type", "course_runs", "thumbnail_url"]
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
        return latest_coupon_version(instance.coupon).payment_version.amount

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


class CouponPaymentSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payments """

    class Meta:
        fields = "__all__"
        model = models.CouponPayment


class CouponPaymentVersionSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payment versions """

    payment = CouponPaymentSerializer()

    class Meta:
        fields = "__all__"
        model = models.CouponPaymentVersion


class BaseCouponSerializer(serializers.Serializer):
    """ Base serializer for coupon creation data """

    name = serializers.CharField(
        max_length=256,
        validators=[UniqueValidator(queryset=CouponPayment.objects.all())],
    )
    tag = serializers.CharField(max_length=256, allow_null=True, required=False)
    amount = serializers.DecimalField(decimal_places=2, max_digits=20)
    automatic = serializers.BooleanField(default=False)
    activation_date = serializers.DateTimeField()
    expiration_date = serializers.DateTimeField()
    product_ids = serializers.ListField(child=serializers.IntegerField())
    max_redemptions = serializers.IntegerField(default=1)
    max_redemptions_per_user = serializers.IntegerField(default=1)
    coupon_type = serializers.ChoiceField(
        choices=set(
            zip(CouponPaymentVersion.COUPON_TYPES, CouponPaymentVersion.COUPON_TYPES)
        )
    )
    num_coupon_codes = serializers.IntegerField(default=1)
    company = serializers.CharField(max_length=512, allow_null=True, required=False)

    def validate_product_ids(self, value):
        """ Determine if the product_ids field is valid """
        if not value or len(value) == 0:
            raise ValidationError("At least one product must be selected")
        products_missing = set(value) - set(
            Product.objects.filter(id__in=value).values_list("id", flat=True)
        )
        if products_missing:
            raise ValidationError(
                "Product with id(s) {} could not be found".format(
                    ",".join(str(pid) for pid in products_missing)
                )
            )
        return value

    def create(self, validated_data):
        with transaction.atomic():
            if validated_data.get("company"):
                company, _ = Company.objects.get_or_create(
                    name=validated_data.get("company")
                )
            else:
                company = None
            payment = CouponPayment.objects.create(name=validated_data.get("name"))
            payment_version = CouponPaymentVersion.objects.create(
                payment=payment,
                company=company,
                tag=validated_data.get("tag"),
                automatic=validated_data.get("automatic", False),
                activation_date=validated_data.get("activation_date"),
                expiration_date=validated_data.get("expiration_date"),
                amount=validated_data.get("amount"),
                num_coupon_codes=validated_data.get("num_coupon_codes"),
                coupon_type=validated_data.get("coupon_type"),
                max_redemptions=validated_data.get("max_redemptions", 1),
                max_redemptions_per_user=1,
                payment_type=validated_data.get("payment_type"),
                payment_transaction=validated_data.get("payment_transaction"),
            )
            for coupon in range(validated_data.get("num_coupon_codes")):
                coupon = Coupon.objects.create(
                    coupon_code=validated_data.get("coupon_code", uuid4().hex),
                    payment=payment,
                )
                CouponVersion.objects.create(
                    coupon=coupon, payment_version=payment_version
                )
                for product_id in validated_data.get("product_ids"):
                    CouponEligibility.objects.create(
                        coupon=coupon, product_id=product_id
                    )
            return payment_version


class SingleUseCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating single-use coupons """

    payment_transaction = serializers.CharField(max_length=256)
    payment_type = serializers.ChoiceField(
        choices=[(_type, _type) for _type in CouponPaymentVersion.PAYMENT_TYPES]
    )


class PromoCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating promo coupons """

    coupon_code = serializers.CharField(
        max_length=50, validators=[UniqueValidator(queryset=Coupon.objects.all())]
    )
    payment_transaction = serializers.CharField(
        max_length=256, allow_null=True, required=False
    )
    payment_type = serializers.ChoiceField(
        choices=[(_type, _type) for _type in CouponPaymentVersion.PAYMENT_TYPES],
        allow_null=True,
        required=False,
    )
