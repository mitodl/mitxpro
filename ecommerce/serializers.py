""" ecommerce serializers """
from uuid import uuid4

from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from courses.models import Course, Program
from courses.constants import DEFAULT_COURSE_IMG_PATH
from courses.serializers import CourseSerializer
from ecommerce import models
from ecommerce.api import latest_product_version, latest_coupon_version


class CompanySerializer(serializers.ModelSerializer):
    """ Company Serializer """

    class Meta:
        fields = "__all__"
        model = models.Company


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
    courses = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    def get_type(self, instance):
        """ Return the product version type """
        return instance.product.content_type.model

    def get_courses(self, instance):
        """ Return the course runs in the product """
        model_class = instance.product.content_type.model_class()
        if model_class is Course:
            courses = [instance.product.content_object]
        elif model_class is Program:
            courses = Course.objects.filter(
                program=instance.product.content_object
            ).order_by("position_in_program")
        else:
            raise ValueError(f"Unexpected product for {model_class}")

        return [CourseSerializer(course).data for course in courses]

    def get_thumbnail_url(self, instance):
        """Return the thumbnail for the course or program"""
        content_object = instance.product.content_object
        catalog_image_url = content_object.catalog_image_url
        return catalog_image_url or static(DEFAULT_COURSE_IMG_PATH)

    class Meta:
        fields = ["id", "price", "description", "type", "courses", "thumbnail_url"]
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
        # decimal fields should be represented as strings to prevent floating point parsing problems
        return str(latest_coupon_version(instance.coupon).payment_version.amount)

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
            {
                **ProductVersionSerializer(
                    instance=latest_product_version(item.product)
                ).data,
                "run_ids": list(
                    models.CourseRunSelection.objects.filter(
                        basket=instance
                    ).values_list("run", flat=True)
                ),
            }
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
    company = CompanySerializer()

    class Meta:
        fields = "__all__"
        model = models.CouponPaymentVersion


class BaseCouponSerializer(serializers.Serializer):
    """ Base serializer for coupon creation data """

    name = serializers.CharField(
        max_length=256,
        validators=[UniqueValidator(queryset=models.CouponPayment.objects.all())],
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
            zip(
                models.CouponPaymentVersion.COUPON_TYPES,
                models.CouponPaymentVersion.COUPON_TYPES,
            )
        )
    )
    company = serializers.CharField(
        max_length=512, allow_null=True, allow_blank=True, required=False
    )

    def validate_product_ids(self, value):
        """ Determine if the product_ids field is valid """
        if not value or len(value) == 0:
            raise ValidationError("At least one product must be selected")
        products_missing = set(value) - set(
            models.Product.objects.filter(id__in=value).values_list("id", flat=True)
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
                company = models.Company.objects.get(id=validated_data.get("company"))
            else:
                company = None
            payment = models.CouponPayment.objects.create(
                name=validated_data.get("name")
            )
            payment_version = models.CouponPaymentVersion.objects.create(
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
                coupon = models.Coupon.objects.create(
                    coupon_code=validated_data.get("coupon_code", uuid4().hex),
                    payment=payment,
                )
                models.CouponVersion.objects.create(
                    coupon=coupon, payment_version=payment_version
                )
                for product_id in validated_data.get("product_ids"):
                    models.CouponEligibility.objects.create(
                        coupon=coupon, product_id=product_id
                    )
            return payment_version


class SingleUseCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating single-use coupons """

    num_coupon_codes = serializers.IntegerField(required=True)
    payment_transaction = serializers.CharField(max_length=256)
    payment_type = serializers.ChoiceField(
        choices=set(
            zip(
                models.CouponPaymentVersion.PAYMENT_TYPES,
                models.CouponPaymentVersion.PAYMENT_TYPES,
            )
        )
    )


class PromoCouponSerializer(BaseCouponSerializer):
    """ Serializer for creating promo coupons """

    num_coupon_codes = serializers.IntegerField(default=1, required=False)
    coupon_code = serializers.CharField(
        max_length=50,
        validators=[UniqueValidator(queryset=models.Coupon.objects.all())],
    )
    payment_transaction = serializers.CharField(
        max_length=256, allow_null=True, required=False, allow_blank=True
    )
    payment_type = serializers.ChoiceField(
        choices=set(
            zip(
                models.CouponPaymentVersion.PAYMENT_TYPES,
                models.CouponPaymentVersion.PAYMENT_TYPES,
            )
        ),
        allow_null=True,
        allow_blank=True,
        required=False,
    )
