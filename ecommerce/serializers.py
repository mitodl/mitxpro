""" ecommerce serializers """
import logging

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import transaction, models as dj_models
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
    get_product_version_price_with_discount,
    get_product_from_querystring_id,
)
from ecommerce.constants import ORDERED_VERSIONS_QSET_ATTR, CYBERSOURCE_CARD_TYPES
from ecommerce.models import Basket
from mitxpro.serializers import WriteableSerializerMethodField
from mitxpro.utils import first_or_none, now_in_utc
from users.serializers import ExtendedLegalAddressSerializer

log = logging.getLogger(__name__)


class CompanySerializer(serializers.ModelSerializer):
    """ Company Serializer """

    class Meta:
        fields = ["id", "name"]
        model = models.Company


class ProductVersionSummarySerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for fetching summary info for receipts """

    content_title = serializers.SerializerMethodField()
    readable_id = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    class Meta:
        fields = ["price", "content_title", "readable_id"]
        model = models.ProductVersion

    def get_content_title(self, instance):
        """Return the title of the program or course run"""
        return instance.product.content_object.title

    def get_readable_id(self, instance):
        """Return the readable_id of the program or course run"""
        return get_readable_id(instance.product.content_object)

    def get_price(self, instance):
        """The price does not need decimal points here"""
        return str(instance.price)


class ProductVersionSerializer(serializers.ModelSerializer):
    """ ProductVersion serializer for viewing/updating items in basket """

    type = serializers.SerializerMethodField()
    object_id = serializers.IntegerField(source="product.object_id", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    run_tag = serializers.SerializerMethodField()
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
            # filter_products=True because the course run must have an associated product.
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

            # filter_products=False because we want to show course runs even if they don't have
            # products, since the product is for the program.
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
        return instance.product.content_object.text_id

    def get_run_tag(self, instance):
        """Return the run_tag of the program run or course run"""
        content_object = instance.product.content_object
        if isinstance(content_object, Program):
            program_run = self.context.get("program_run")
            return None if not program_run else program_run.run_tag
        else:
            return content_object.run_tag

    def get_start_date(self, instance):
        """Returns the start date of the program or course run"""
        content_object = instance.product.content_object
        if isinstance(content_object, CourseRun) and content_object.start_date:
            return content_object.start_date.isoformat()
        elif isinstance(content_object, Program) and content_object.next_run_date:
            program_run = self.context.get("program_run")
            if program_run:
                return program_run.start_date.isoformat()
            else:
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
            "run_tag",
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
        fields = ["id", "product_type", "visible_in_bulk_form"]
        model = models.Product


class ProductDetailSerializer(BaseProductSerializer):
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
    def _serialize_item(cls, *, basket_item, basket, context):
        """
        Serialize a BasketItem

        Args:
            basket_item (BasketItem): A basket item
            basket (Basket): A basket
            context (dict): Context from the BasketSerializer

        Returns:
            dict:
                A serialized representation
        """
        if basket_item.program_run:
            context["program_run"] = basket_item.program_run
        serialized_product_version = ProductVersionSerializer(
            instance=latest_product_version(basket_item.product), context=context
        ).data
        valid_run_ids = set()
        for course in serialized_product_version["courses"]:
            valid_run_ids = valid_run_ids.union(
                {run["id"] for run in course["courseruns"]}
            )
        run_ids = list(
            models.CourseRunSelection.objects.filter(
                basket=basket, run_id__in=valid_run_ids
            ).values_list("run", flat=True)
        )
        return {**serialized_product_version, "run_ids": run_ids}

    def get_items(self, instance):
        """ Get the basket items """
        return [
            self._serialize_item(
                basket_item=item, basket=instance, context=self.context
            )
            for item in instance.basketitems.select_related("program_run").all()
        ]

    def get_coupons(self, instance):
        """ Get the basket coupons """
        return CouponSelectionSerializer(
            instance.couponselection_set.all(), many=True
        ).data

    def get_data_consents(self, instance):
        """ Get the DataConsentUser objects associated with the basket via coupon and product"""
        data_consents = get_or_create_data_consents(instance)
        return DataConsentUserSerializer(instance=data_consents, many=True).data

    @classmethod
    def _get_applicable_coupon_version(cls, basket, product, coupons):
        """
        Helper function to determine if the basket coupon should be updated, removed, or kept as is.

        Args:
            basket (Basket): the basket to update
            product (Product): the product coupon should apply to
            coupons (list of JSON objects): Basket coupons to update, or clear if empty list, or leave as is if None

        Returns:
            CouponVersion: CouponVersion object to assign to basket, if any.

        """
        product_version = product.latest_version
        if coupons:
            coupon_code = coupons[0].get("code")
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

    @classmethod
    def _update_basket_data(
        cls,
        basket,
        updated_product=None,
        updated_run_ids=None,
        program_run=None,
        should_update_program_run=False,
        coupon_version=None,
        data_consents=None,
        clear_all=False,
    ):  # pylint: disable=too-many-arguments
        """
        Creates/updates/deletes Basket-related data

        Args:
            basket (models.Basket): The user's Basket
            updated_product (models.Product): If provided, indicates a new Product that differs from the
                previous Product associated with the Basket
            updated_run_ids (iterable of int): If provided, indicates a new selection of CourseRun ids for
                this basket
            program_run (courses.models.ProgramRun): The program run associated with the product in the basket
            should_update_program_run (bool): If True, indicates that the program run associated with the basket
                item should be updated
            coupon_version (models.CouponVersion): A valid coupon to associate with this Basket. If None, all
                coupon selections for the Basket are deleted
            data_consents (iterable of int): Data consent ids
            clear_all (boolean): If True, clears the basket, i.e.: all basket items, course run selections,
                and coupon selections are deleted
        """
        with transaction.atomic():
            # Fetching the basket again using select_for_update to avoid ending up in a weird state
            # if concurrent requests are received.
            basket = Basket.objects.select_for_update().get(id=basket.id)
            if clear_all is True:
                basket.basketitems.all().delete()
            if clear_all is True or updated_run_ids is not None:
                basket.courserunselection_set.all().delete()
            if clear_all is True or coupon_version is None:
                basket.couponselection_set.all().delete()

            if updated_product is not None or should_update_program_run is True:
                update_dict = dict(quantity=1)
                if updated_product is not None:
                    update_dict["product"] = updated_product
                if should_update_program_run is True:
                    update_dict["program_run"] = program_run
                models.BasketItem.objects.update_or_create(
                    basket=basket, defaults=update_dict
                )
            if updated_run_ids is not None:
                models.CourseRunSelection.objects.bulk_create(
                    models.CourseRunSelection(basket=basket, run_id=run_id)
                    for run_id in updated_run_ids
                )
            if coupon_version is not None:
                models.CouponSelection.objects.update_or_create(
                    basket=basket, defaults={"coupon": coupon_version.coupon}
                )
            if data_consents is not None:
                models.DataConsentUser.objects.filter(
                    id__in=data_consents, user=basket.user
                ).update(consent_date=now_in_utc())

    def _fetch_and_validate_product(self, items):
        """
        Fetches the product associated with the product id in the request, paired with a program
        run indicated by that id (or None if the id does not indicate a program run)

        Args:
            items (list of dict): The items from the request body

        Returns:
            (models.Product, courses.models.ProgramRun): The Product paired with an asociated ProgramRun
                if one exists (or None if one does not exist)
        """
        item = items[0]
        request_product_id = item.get("product_id")
        try:
            product, _, program_run = get_product_from_querystring_id(
                request_product_id
            )
        except (ObjectDoesNotExist, MultipleObjectsReturned) as exc:
            if isinstance(exc, MultipleObjectsReturned):
                log.error(
                    "Multiple Products found with identical ids: %s", request_product_id
                )
            raise ValidationError(
                {"items": f"Invalid product id {request_product_id}"}
            ) from exc
        return product, program_run

    def _validate_and_compare_runs(self, basket, items, product):
        """
        Compares course run selections in the request with the ones that already exist for this
        Basket. If they are different, the updated ids are returned.

        Args:
            basket (models.Basket):
            items (list of dict): The items from the request body
            product (models.Product): The Product currently associated with the given Basket

        Returns:
            set of int: A set of updated course run id selections (or None if they were not changed)
        """
        item = items[0]
        run_ids = set(item.get("run_ids", []))
        self._validate_runs(run_ids, product)
        existing_run_ids = set(
            basket.courserunselection_set.values_list("run_id", flat=True)
        )
        return run_ids if run_ids != existing_run_ids else None

    def update(self, instance, validated_data):  # pylint: disable=too-many-locals
        items = validated_data.get("items")
        coupons = validated_data.get("coupons")
        data_consents = validated_data.get("data_consents")
        basket = instance

        self._validate_coupons(coupons)

        if items is None and coupons is None and data_consents is None:
            raise ValidationError("Invalid request")

        if items == []:
            self._update_basket_data(
                basket, data_consents=data_consents, clear_all=True
            )
            return basket

        existing_item = basket.basketitems.select_related(
            "product", "program_run"
        ).first()
        existing_product, existing_program_run = (
            (None, None)
            if existing_item is None
            else (existing_item.product, existing_item.program_run)
        )
        coupon_version = None

        if items is None:
            updated_product = None
            updated_run_ids = None
            program_run = None
            should_update_program_run = False
        else:
            product, program_run = self._fetch_and_validate_product(items)
            updated_product = product if product != existing_product else None
            updated_run_ids = self._validate_and_compare_runs(basket, items, product)
            should_update_program_run = program_run != existing_program_run

        if updated_product or existing_product:
            coupon_version = self._get_applicable_coupon_version(
                basket,
                # Whether or not the product was updated, we want to make sure that there is a valid
                # coupon associated with the basket
                product=updated_product or existing_product,
                coupons=coupons,
            )

        self._update_basket_data(
            basket,
            updated_product=updated_product,
            updated_run_ids=updated_run_ids,
            program_run=program_run,
            should_update_program_run=should_update_program_run,
            coupon_version=coupon_version,
            data_consents=data_consents,
            clear_all=False,
        )
        return basket

    @staticmethod
    def _validate_coupons(coupons):
        """
        Validates coupons provided in the request.
        NOTE: This is not being done in a standard field validator function (validate_*) because our
        front end expects these error values to be a simple string, and standard DRF field validators
        put a list of strings in the body when you raise a ValidationError

        Args:
            coupons (list): Coupon data from the request body

        Raises:
            ValidationError: Raised if the coupon data is in the wrong format
        """
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

    def _validate_runs(self, run_ids, product):
        """
        Validates the run ids provided in the request.
        NOTE: This is not being done in a standard field validator function (validate_*) because our
        front end expects these error values to be a simple string, and standard DRF field validators
        put a list of strings in the body when you raise a ValidationError

        Args:
            run_ids (set of int): A set of CourseRun ids
            product (models.Product): The Product referred to in the request
        Raises:
            ValidationError: Raised if the run ids provided are invalid
        """
        if run_ids is not None and len(run_ids) > 0:
            if None in run_ids:
                raise ValidationError(
                    {"runs": "Each course must have a course run selection"}
                )
            if CourseRunEnrollment.objects.filter(
                user=self.instance.user, run_id__in=run_ids
            ).exists():
                raise ValidationError(
                    {
                        "runs": "User has already enrolled in one of the selected course runs"
                    }
                )
        product_run_course_map = dict(
            product.run_queryset.filter(id__in=run_ids).values_list("id", "course_id")
        )
        if len(product_run_course_map) < len(run_ids):
            missing_run_ids = set(run_ids) - set(product_run_course_map.keys())
            raise ValidationError(
                {"runs": f"Unable to find run(s) with id(s) {missing_run_ids}"}
            )
        elif len(set(product_run_course_map.values())) < len(run_ids):
            raise ValidationError({"runs": "Only one run per course can be selected"})

    def validate_items(self, items):
        """Validate some basic things about items"""
        if items:
            if len(items) > 1:
                raise ValidationError("Basket cannot contain more than one item")
            item = items[0]
            product_id = item.get("product_id")
            if product_id is None:
                raise ValidationError("Invalid request")
        return {"items": items}

    def validate_coupons(self, coupons):
        """No-op validator function for coupon data in the request body"""
        return {"coupons": coupons}

    def validate_data_consents(self, data_consents):
        """Validate that DataConsentUser objects exist"""
        if data_consents:
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
    include_future_runs = serializers.BooleanField()

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
            include_future_runs=validated_data.get("include_future_runs"),
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


class LineSummarySerializer(serializers.ModelSerializer):
    """ Summary serializer for Line model """

    product_version = ProductVersionSummarySerializer()

    class Meta:
        model = models.Line
        fields = ["product_version", "quantity"]


class OrderReceiptSerializer(serializers.ModelSerializer):
    """ Serializer for extracting receipt info from an Order object"""

    lines = serializers.SerializerMethodField()
    purchaser = serializers.SerializerMethodField()
    coupon = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    receipt = serializers.SerializerMethodField()

    def get_receipt(self, instance):
        """Get receipt information if it exists"""
        receipt = instance.receipt_set.order_by("-created_on").first()
        if receipt and (
            "req_card_number" in receipt.data or "req_card_type" in receipt.data
        ):
            data = {"card_number": None, "card_type": None}
            if "req_card_number" in receipt.data:
                data["card_number"] = receipt.data["req_card_number"]
            if (
                "req_card_type" in receipt.data
                and receipt.data["req_card_type"] in CYBERSOURCE_CARD_TYPES
            ):
                data["card_type"] = CYBERSOURCE_CARD_TYPES[
                    receipt.data["req_card_type"]
                ]
            return data
        return None

    def get_lines(self, instance):
        """ Get product information along with applied discounts """
        coupon_redemption = instance.couponredemption_set.first()
        lines = []
        for line in instance.lines.all():
            total_paid = line.product_version.price * line.quantity
            discount = 0.0
            dates = CourseRunEnrollment.objects.filter(
                order_id=instance.id, change_status__isnull=True
            ).aggregate(
                start_date=dj_models.Min("run__start_date"),
                end_date=dj_models.Max("run__end_date"),
            )
            if coupon_redemption:
                total_paid = (
                    get_product_version_price_with_discount(
                        coupon_version=coupon_redemption.coupon_version,
                        product_version=line.product_version,
                    )
                    * line.quantity
                )
                discount = line.product_version.price - total_paid
            lines.append(
                dict(
                    quantity=line.quantity,
                    total_paid=str(total_paid),
                    discount=str(discount),
                    **ProductVersionSummarySerializer(line.product_version).data,
                    start_date=dates["start_date"],
                    end_date=dates["end_date"],
                )
            )
        return lines

    def get_order(self, instance):
        """Get order-specific information"""
        return dict(
            id=instance.id,
            created_on=instance.created_on,
            reference_number=instance.reference_number,
        )

    def get_coupon(self, instance):
        """Get coupon code from the coupon redemption if available"""
        coupon_redemption = instance.couponredemption_set.first()
        if not coupon_redemption:
            return None
        return coupon_redemption.coupon_version.coupon.coupon_code

    def get_purchaser(self, instance):
        """Get the purchaser infrmation"""
        return ExtendedLegalAddressSerializer(instance.purchaser.legal_address).data

    class Meta:
        fields = ["purchaser", "lines", "coupon", "order", "receipt"]
        model = models.Order
