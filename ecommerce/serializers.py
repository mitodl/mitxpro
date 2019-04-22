""" ecommerce serializers """
from uuid import uuid4
from datetime import datetime

import pytz
from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from rest_framework.response import Response

from courses.models import Course, CourseRun, Program
from courses.constants import DEFAULT_COURSE_IMG_PATH
from courses.serializers import CourseSerializer
from ecommerce import models
from ecommerce.api import (
    best_coupon_for_product,
    get_valid_coupon_versions,
    latest_coupon_version,
    latest_product_version,
    get_data_consents,
)
from ecommerce.models import DataConsentUser


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
    data_consents = serializers.SerializerMethodField()

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

    @classmethod
    def _get_runs_for_product(cls, *, product_version, run_ids):
        """Helper function to get and validate selected runs in a product"""
        content_object = product_version.product.content_object
        runs_for_product = CourseRun.objects.filter(id__in=run_ids)
        if isinstance(content_object, Course):
            runs_for_product = runs_for_product.filter(course=content_object)
        elif isinstance(content_object, Program):
            runs_for_product = runs_for_product.filter(course__program=content_object)
        else:
            raise ValidationError(
                f"Unknown content_object for {product_version.product}"
            )

        run_ids_for_product = {run.id for run in runs_for_product}

        missing_run_ids = set(run_ids) - run_ids_for_product
        if missing_run_ids:
            raise ValidationError(f"Unable to find run(s) with id(s) {missing_run_ids}")

        courses_for_product = set(runs_for_product.values_list("course", flat=True))
        if len(courses_for_product) < len(run_ids):
            raise ValidationError("Only one run per course can be selected")

        if models.CourseRunEnrollment.objects.filter(run_id__in=run_ids).exists():
            raise ValidationError("User has already enrolled in run")

        return runs_for_product

    @classmethod
    def _update_items(cls, basket, items):
        """
        Helper function to determine if the basket item should be updated, removed, or kept as is.

        Args:
            basket (Basket): the basket to update
            items (list of JSON objects): Basket items to update, or clear if empty list, or leave as is if None

        Returns:
            tuple: ProductVersion object to assign to basket, if any, and a list of CourseRun

        """
        if items:
            # Item updated
            item = items[0]
            product_version_id = item.get("id")
            run_ids = item.get("run_ids")

            product_version = models.ProductVersion.objects.get(id=product_version_id)
            if run_ids is not None:
                runs = cls._get_runs_for_product(
                    product_version=product_version, run_ids=run_ids
                )
            else:
                runs = None
        elif items is not None:
            # Item removed
            product_version = None
            runs = None
        else:
            # Item has not changed
            product_version = latest_product_version(basket.basketitems.first().product)
            runs = list(CourseRun.objects.filter(courserunselection__basket=basket))
        return product_version, runs

    @classmethod
    def _update_coupons(cls, basket, product_version, coupons):
        """
        Helper function to determine if the basket coupon should be updated, removed, or kept as is.

        Args:
            basket (Basket): the basket to update
            product_version (ProductVersion): the product version coupon should apply to
            coupons (list of JSON objects): Basket coupons to update, or clear if empty list, or leave as is if None

        Returns:
            CouponVersion: CouponVersion object to assign to basket, if any.

        """
        if not product_version:
            # No product, so clear coupon too
            return None

        if coupons:
            if len(coupons) > 1:
                raise ValidationError("Basket cannot contain more than one coupon")
            coupon = coupons[0]
            if not isinstance(coupon, dict):
                raise ValidationError("Invalid request")
            coupon_code = coupon.get("code")
            if coupon_code is None:
                raise ValidationError("Invalid request")

            # Check if the coupon is valid for the product
            coupon_version = best_coupon_for_product(
                product_version.product, basket.user, code=coupon_code
            )
            if coupon_version is None:
                raise ValidationError("Coupon code {} is invalid".format(coupon_code))
        elif coupons is not None:
            # Coupon was cleared, get the best available auto coupon for the product instead
            coupon_version = best_coupon_for_product(
                product_version.product, basket.user, auto_only=True
            )
        else:
            # coupon was not changed, make sure it is still valid; if not, replace with best auto coupon if any.
            coupon_selection = basket.couponselection_set.first()
            if coupon_selection:
                coupon_version = latest_coupon_version(coupon_selection.coupon)
            else:
                coupon_version = None
            valid_coupon_versions = get_valid_coupon_versions(
                product_version.product, basket.user
            )
            if coupon_version is None or coupon_version not in valid_coupon_versions:
                coupon_version = best_coupon_for_product(
                    product_version.product, basket.user, auto_only=True
                )
        return coupon_version

    def update(self, instance, validated_data):
        items = validated_data.get("items")
        coupons = validated_data.get("coupons")
        data_consents = validated_data.get("data_consents")
        basket = instance

        if data_consents is not None:
            try:
                for consent_id in data_consents:
                    data_consent_user = DataConsentUser.objects.get(id=consent_id)
                    data_consent_user.consent_date = datetime.now(tz=pytz.UTC)
                    data_consent_user.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data=BasketSerializer(instance=basket).data,
                )
            except DataConsentUser.DoesNotExist:
                raise ValidationError("data consent does not exist")

        elif items is None and coupons is None:
            raise ValidationError("Invalid request")
        else:
            product_version, runs = self._update_items(basket, items)
            coupon_version = self._update_coupons(basket, product_version, coupons)
            if product_version:
                # Update basket items and coupon selection
                with transaction.atomic():
                    basket.basketitems.all().delete()
                    models.BasketItem.objects.create(
                        product=product_version.product, quantity=1, basket=basket
                    )

                    if runs is not None:
                        models.CourseRunSelection.objects.filter(basket=basket).delete()
                        for run in runs:
                            models.CourseRunSelection.objects.create(basket=basket, run=run)

                    if coupon_version:
                        models.CouponSelection.objects.update_or_create(
                            basket=basket, defaults={"coupon": coupon_version.coupon}
                        )
                    else:
                        basket.couponselection_set.all().delete()
            else:
                # Remove everything from basket
                with transaction.atomic():
                    basket.basketitems.all().delete()
                    basket.couponselection_set.all().delete()
        return instance

    def validate_items(self, items):
        """Validate some basic things about items"""
        if items:
            if len(items) > 1:
                raise ValidationError("Basket cannot contain more than one item")
            item = items[0]
            product_version_id = item.get("id")

            if product_version_id is None:
                raise ValidationError("Invalid request")
            if not models.ProductVersion.objects.filter(id=product_version_id).exists():
                raise ValidationError(
                    f"Invalid product version id {product_version_id}"
                )

        return {"items": items}

    def validate_coupons(self, coupons):
        """Can't do much validation here since we don't have the product version id"""
        return {"coupons": coupons}

    def get_agreements(self, instance):
        """ Get the basket unsigned data consent agreements """
        return [agreement.id for agreement in get_data_consents(instance)]

    def get_data_consents(self, instance):
        """ Get the basket data consent agreements for basket user"""
        return [
            DataConsentUserSerializer(instance=consent_user).data
            for consent_user in get_data_consents(instance)
        ]

    class Meta:
        fields = ["items", "coupons", "data_consents"]
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


class DataConsentUserSerializer(serializers.ModelSerializer):
    """ Serializer for DataConsentUsers """

    class Meta:
        fields = "__all__"
        model = models.DataConsentUser
