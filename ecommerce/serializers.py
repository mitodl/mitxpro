""" ecommerce serializers """
from datetime import datetime

import pytz
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from courses.models import Course, CourseRun, Program, CourseRunEnrollment
from courses.constants import DEFAULT_COURSE_IMG_PATH
from ecommerce import models
from ecommerce.api import (
    best_coupon_for_product,
    create_coupons,
    get_readable_id,
    get_valid_coupon_versions,
    latest_coupon_version,
    latest_product_version,
    get_or_create_data_consents,
)
from ecommerce.constants import ORDERED_VERSIONS_QSET_ATTR
from mitxpro.serializers import WriteableSerializerMethodField
from mitxpro.utils import first_or_none


class CompanySerializer(serializers.ModelSerializer):
    """ Company Serializer """

    class Meta:
        fields = ["id", "name"]
        model = models.Company


class ProductVersionSerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for viewing/updating items in basket """

    type = serializers.SerializerMethodField()
    object_id = serializers.IntegerField(source="product.object_id", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    courses = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    content_title = serializers.SerializerMethodField()
    readable_id = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()

    def get_type(self, instance):
        """ Return the product version type """
        return instance.product.content_type.model

    def get_courses(self, instance):
        """ Return the courses in the product """
        from courses.serializers import CourseSerializer

        model_class = instance.product.content_type.model_class()
        if model_class is CourseRun:
            return [
                CourseSerializer(
                    instance.product.content_object.course,
                    context={**self.context, "filter_products": True},
                ).data
            ]
        elif model_class is Program:
            courses = Course.objects.filter(
                program=instance.product.content_object
            ).order_by("position_in_program")

            return CourseSerializer(
                courses, many=True, context={**self.context, "filter_products": False}
            ).data
        else:
            raise ValueError(f"Unexpected product for {model_class}")

    def get_thumbnail_url(self, instance):
        """Return the thumbnail for the courserun or program"""
        content_object = instance.product.content_object
        if isinstance(content_object, Program):
            catalog_image_url = content_object.catalog_image_url
        elif isinstance(content_object, CourseRun):
            catalog_image_url = content_object.course.catalog_image_url
        else:
            raise ValueError(f"Unexpected product {content_object}")
        return catalog_image_url or static(DEFAULT_COURSE_IMG_PATH)

    def get_content_title(self, instance):
        """Return the title of the program or course run"""
        return instance.product.content_object.title

    def get_readable_id(self, instance):
        """Return the readable_id of the program or course run"""
        return get_readable_id(instance.product.content_object)

    def get_start_date(self, instance):
        """Returns the start date of the program or course run"""
        content_object = instance.product.content_object
        if isinstance(content_object, CourseRun) and content_object.start_date:
            return content_object.start_date.isoformat()
        elif isinstance(content_object, Program) and content_object.next_run_date:
            return content_object.next_run_date.isoformat()
        return None

    class Meta:
        fields = [
            "id",
            "price",
            "description",
            "content_title",
            "type",
            "courses",
            "thumbnail_url",
            "object_id",
            "product_id",
            "readable_id",
            "created_on",
            "start_date",
        ]
        model = models.ProductVersion


class BaseProductSerializer(serializers.ModelSerializer):
    """ Basic Product Serializer """

    product_type = serializers.SerializerMethodField()

    def get_product_type(self, instance):
        """ Return the product type """
        return instance.content_type.model

    class Meta:
        fields = ["id", "product_type"]
        model = models.Product


class ProductSerializer(BaseProductSerializer):
    """ Product Serializer """

    title = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()

    def get_title(self, instance):
        """ Return the product title """
        return instance.content_type.get_object_for_this_type(
            pk=instance.object_id
        ).title

    def get_latest_version(self, instance):
        """Serialize and return the latest ProductVersion for the Product"""
        # The Django ORM can be used to
        has_ordered_versions = self.context.get("has_ordered_versions", False)
        latest_version = (
            instance.latest_version
            if not has_ordered_versions
            else first_or_none(getattr(instance, ORDERED_VERSIONS_QSET_ATTR, []))
        )
        return ProductVersionSerializer(
            latest_version, context={**self.context, "all_runs": True}
        ).data

    class Meta:
        fields = BaseProductSerializer.Meta.fields + ["title", "latest_version"]
        model = models.Product


class ProductDetailSerializer(ProductSerializer):
    """Product Serializer with ProductVersion detail included"""

    latest_version = serializers.SerializerMethodField()

    def get_latest_version(self, instance):
        """Serialize and return the latest ProductVersion for the Product"""
        return ProductVersionSerializer(
            instance.latest_version, context={**self.context, "all_runs": True}
        ).data

    class Meta:
        fields = ProductSerializer.Meta.fields + ["latest_version"]
        model = models.Product


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


class CouponSerializer(serializers.ModelSerializer):
    """Coupon serializer"""

    name = serializers.SerializerMethodField()

    def get_name(self, instance):
        """Get the 'name' property of the associated CouponPayment"""
        return instance.payment.name

    class Meta:
        exclude = ("payment", "created_on", "updated_on")
        model = models.Coupon


class BasketSerializer(serializers.ModelSerializer):
    """Basket model serializer"""

    items = WriteableSerializerMethodField()
    coupons = WriteableSerializerMethodField()
    data_consents = WriteableSerializerMethodField()

    @classmethod
    def _serialize_item(cls, *, item, basket, context):
        """
        Serialize a BasketItem

        Args:
            item (BasketItem): A basket item
            basket (Basket): A basket
            context (dict): Context from the BasketSerializer

        Returns:
            dict:
                A serialized representation
        """
        serialized_product_version = ProductVersionSerializer(
            instance=latest_product_version(item.product), context=context
        ).data
        valid_run_ids = set()
        for course in serialized_product_version["courses"]:
            for run in course["courseruns"]:
                valid_run_ids.add(run["id"])
        run_ids = [
            run_id
            for run_id in models.CourseRunSelection.objects.filter(
                basket=basket
            ).values_list("run", flat=True)
            if run_id in valid_run_ids
        ]
        return {**serialized_product_version, "run_ids": run_ids}

    def get_items(self, instance):
        """ Get the basket items """
        return [
            self._serialize_item(item=item, basket=instance, context=self.context)
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

    def get_data_consents(self, instance):
        """ Get the DataConsentUser objects associated with the basket via coupon and product"""
        data_consents = get_or_create_data_consents(instance)
        return DataConsentUserSerializer(instance=data_consents, many=True).data

    @classmethod
    def _get_runs_for_product(cls, *, product, run_ids, user):
        """Helper function to get and validate selected runs in a product"""
        if None in run_ids:
            raise ValidationError(
                {"runs": "Each course must have a course run selection"}
            )

        runs_for_product = list(product.run_queryset.filter(id__in=run_ids))
        run_ids_for_product = {run.id for run in runs_for_product}

        missing_run_ids = set(run_ids) - run_ids_for_product
        if missing_run_ids:
            raise ValidationError(
                {"runs": f"Unable to find run(s) with id(s) {missing_run_ids}"}
            )

        courses_for_product = {}
        for run in runs_for_product:
            if run.course_id not in courses_for_product:
                courses_for_product[run.course_id] = run.id
            elif courses_for_product[run.course_id] != run.id:
                raise ValidationError(
                    {"runs": "Only one run per course can be selected"}
                )

        if CourseRunEnrollment.objects.filter(user=user, run_id__in=run_ids).exists():
            raise ValidationError({"runs": "User has already enrolled in run"})

        return runs_for_product

    @classmethod
    def _update_items(cls, basket, items):
        """
        Helper function to determine if the basket item should be updated, removed, or kept as is.

        Args:
            basket (Basket): the basket to update
            items (list of JSON objects): Basket items to update, or clear if empty list, or leave as is if None

        Returns:
            tuple: Product object to assign to basket, if any, and a list of CourseRun

        """
        if items:
            # Item updated
            item = items[0]
            product_id = item.get("product_id")
            run_ids = item.get("run_ids")
            product = models.Product.objects.get(id=product_id)
            previous_product = models.Product.objects.filter(
                basketitem__basket=basket
            ).first()

            if (
                run_ids is None
                and previous_product is not None
                and product_id == previous_product.id
            ):
                # User is updating basket item to the same item as before
                run_ids = list(
                    models.CourseRunSelection.objects.filter(basket=basket).values_list(
                        "run", flat=True
                    )
                )

            if run_ids is not None:
                runs = cls._get_runs_for_product(
                    product=product, run_ids=run_ids, user=basket.user
                )
            else:
                runs = None
        elif items is not None:
            # Item removed
            product = None
            runs = None
        else:
            # Item has not changed
            basket_item = basket.basketitems.first()
            product = basket_item.product if basket_item else None
            runs = list(CourseRun.objects.filter(courserunselection__basket=basket))
        return product, runs

    @classmethod
    def _update_coupons(cls, basket, product, coupons):
        """
        Helper function to determine if the basket coupon should be updated, removed, or kept as is.

        Args:
            basket (Basket): the basket to update
            product (Product): the product coupon should apply to
            coupons (list of JSON objects): Basket coupons to update, or clear if empty list, or leave as is if None

        Returns:
            CouponVersion: CouponVersion object to assign to basket, if any.

        """
        if not product:
            # No product, so clear coupon too
            return None

        product_version = product.latest_version
        if coupons:
            if len(coupons) > 1:
                raise ValidationError(
                    {"coupons": "Basket cannot contain more than one coupon"}
                )
            coupon = coupons[0]
            if not isinstance(coupon, dict):
                raise ValidationError({"coupons": "Invalid request"})
            coupon_code = coupon.get("code")
            if coupon_code is None:
                raise ValidationError({"coupons": "Invalid request"})

            # Check if the coupon is valid for the product
            coupon_version = best_coupon_for_product(
                product_version.product, basket.user, code=coupon_code
            )
            if coupon_version is None:
                raise ValidationError(
                    {
                        "coupons": "Enrollment / Promotional Code {} is invalid".format(
                            coupon_code
                        )
                    }
                )
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

        if items is None and coupons is None and data_consents is None:
            raise ValidationError("Invalid request")

        product, runs = self._update_items(basket, items)
        coupon_version = self._update_coupons(basket, product, coupons)
        with transaction.atomic():
            if product:
                # Update basket items and coupon selection
                basket.basketitems.all().delete()
                models.BasketItem.objects.create(
                    product=product, quantity=1, basket=basket
                )

                models.CourseRunSelection.objects.filter(basket=basket).delete()
                if runs is not None:
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
                basket.basketitems.all().delete()
                basket.couponselection_set.all().delete()
                basket.courserunselection_set.all().delete()

            if data_consents is not None:
                sign_date = datetime.now(tz=pytz.UTC)
                models.DataConsentUser.objects.filter(
                    id__in=data_consents, user=basket.user
                ).update(consent_date=sign_date)

        return instance

    def validate_items(self, items):
        """Validate some basic things about items"""
        if items:
            if len(items) > 1:
                raise ValidationError("Basket cannot contain more than one item")
            item = items[0]
            product_id = item.get("product_id")

            if product_id is None:
                raise ValidationError("Invalid request")
            if not models.ProductVersion.objects.filter(
                product__id=product_id
            ).exists():
                raise ValidationError(f"Invalid product id {product_id}")
            product = models.Product.all_objects.filter(id=product_id).first()
            if not product.is_active:
                raise ValidationError(f"Product id {product_id} is not active")

        return {"items": items}

    def validate_coupons(self, coupons):
        """
        Can't do much validation at this point since we don't have the product version id. Instead
        this is done above in _update_coupons.
        """
        return {"coupons": coupons}

    def validate_data_consents(self, data_consents):
        """Validate that DataConsentUser objects exist"""
        valid_consent_ids = set(
            models.DataConsentUser.objects.filter(id__in=data_consents).values_list(
                "id", flat=True
            )
        )
        invalid_consent_ids = set(data_consents) - valid_consent_ids
        if invalid_consent_ids:
            raise ValidationError(
                f"Invalid data consent id {','.join([str(consent_id) for consent_id in invalid_consent_ids])}"
            )
        return {"data_consents": data_consents}

    class Meta:
        fields = ["items", "coupons", "data_consents"]
        model = models.Basket


class CouponPaymentSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payments """

    class Meta:
        fields = "__all__"
        model = models.CouponPayment


class CurrentCouponPaymentSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payments with their most recent version """

    version = serializers.SerializerMethodField()

    def get_version(self, instance):
        """ Serializes the most recent associated CouponPaymentVersion """
        latest_version = (
            self.context.get("latest_version", None) or instance.latest_version
        )
        return CouponPaymentVersionSerializer(latest_version).data

    class Meta:
        fields = "__all__"
        model = models.CouponPayment


class CouponPaymentVersionSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payment versions """

    class Meta:
        fields = "__all__"
        model = models.CouponPaymentVersion


class CouponPaymentVersionDetailSerializer(serializers.ModelSerializer):
    """ Serializer for coupon payment versions and related objects """

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
    amount = serializers.DecimalField(
        decimal_places=5,
        max_digits=20,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
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
        return create_coupons(
            company_id=validated_data.get("company"),
            tag=validated_data.get("tag"),
            name=validated_data.get("name"),
            automatic=validated_data.get("automatic", False),
            activation_date=validated_data.get("activation_date"),
            expiration_date=validated_data.get("expiration_date"),
            amount=validated_data.get("amount"),
            num_coupon_codes=validated_data.get("num_coupon_codes"),
            coupon_type=validated_data.get("coupon_type"),
            max_redemptions=validated_data.get("max_redemptions", 1),
            payment_type=validated_data.get("payment_type"),
            payment_transaction=validated_data.get("payment_transaction"),
            coupon_code=validated_data.get("coupon_code"),
            product_ids=validated_data.get("product_ids"),
        )


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

    company = serializers.SerializerMethodField()
    consent_text = serializers.SerializerMethodField()

    def get_company(self, instance):
        """Get serialized company version"""
        return CompanySerializer(instance.agreement.company).data

    def get_consent_text(self, instance):
        """Get text for the agreement"""
        return instance.agreement.content

    class Meta:
        fields = ["consent_date", "id", "company", "consent_text"]
        model = models.DataConsentUser
