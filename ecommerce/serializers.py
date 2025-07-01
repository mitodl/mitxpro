"""ecommerce serializers"""

import logging
from decimal import Decimal

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models as dj_models
from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from courses.constants import DEFAULT_COURSE_IMG_PATH
from courses.models import Course, CourseRun, CourseRunEnrollment, Program, ProgramRun
from ecommerce import models
from ecommerce.api import (
    best_coupon_for_product,
    create_coupons,
    determine_visitor_country,
    get_or_create_data_consent_users,
    get_product_from_querystring_id,
    get_product_version_price_with_discount_tax,
    get_valid_coupon_versions,
    latest_coupon_version,
    latest_product_version,
)
from ecommerce.constants import CYBERSOURCE_CARD_TYPES, DISCOUNT_TYPES
from ecommerce.models import Basket, TaxRate
from ecommerce.utils import CouponUtils, validate_amount
from mitxpro.serializers import WriteableSerializerMethodField
from mitxpro.utils import now_in_utc
from users.serializers import ExtendedLegalAddressSerializer

log = logging.getLogger(__name__)


class CompanySerializer(serializers.ModelSerializer):
    """Company Serializer"""

    class Meta:
        fields = ["id", "name"]
        model = models.Company


class BaseProductVersionSerializer(serializers.ModelSerializer):
    """ProductVersion serializer for fetching summary info for receipts"""

    content_title = serializers.SerializerMethodField()
    readable_id = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    def get_content_title(self, instance):
        """Return the title of the program or course run"""
        return instance.product.content_object.title

    def get_readable_id(self, instance):
        """Return the text id of the program or course run"""
        return instance.product.content_object.text_id

    def get_price(self, instance):
        """Return the product version price"""
        return str(instance.price)

    class Meta:
        fields = ["price", "content_title", "readable_id"]
        model = models.ProductVersion


class ProductVersionSerializer(BaseProductVersionSerializer):
    """ProductVersion serializer"""

    object_id = serializers.IntegerField(source="product.object_id", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    type = serializers.SerializerMethodField()

    def get_type(self, instance):
        """Return the content type of the product version's product"""
        return instance.product.content_type.model

    class Meta:
        fields = BaseProductVersionSerializer.Meta.fields + [  # noqa: RUF005
            "id",
            "object_id",
            "product_id",
            "type",
        ]
        model = models.ProductVersion


class FullProductVersionSerializer(ProductVersionSerializer):
    """ProductVersion serializer for viewing/updating items in basket"""

    start_date = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    run_tag = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()

    def get_courses(self, instance):
        """Return the courses in the product"""
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
            raise ValueError(f"Unexpected product for {model_class}")  # noqa: EM102

    def get_thumbnail_url(self, instance):
        """Return the thumbnail for the courserun or program"""
        content_object = instance.product.content_object
        if isinstance(content_object, Program):
            catalog_image_url = content_object.catalog_image_url
        elif isinstance(content_object, CourseRun):
            catalog_image_url = content_object.course.catalog_image_url
        else:
            raise ValueError(f"Unexpected product {content_object}")  # noqa: EM102, TRY004
        return catalog_image_url or static(DEFAULT_COURSE_IMG_PATH)

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
        fields = ProductVersionSerializer.Meta.fields + [  # noqa: RUF005
            "start_date",
            "thumbnail_url",
            "run_tag",
            "courses",
            "description",
            "created_on",
        ]
        model = models.ProductVersion


class ProgramProductContentObjectSerializer(serializers.ModelSerializer):
    """Product serializer for Program"""

    readable_id = serializers.CharField(source="text_id")

    class Meta:
        fields = ["id", "title", "readable_id"]
        model = Program


class CourseRunProductContentObjectSerializer(serializers.ModelSerializer):
    """Product serializer for CourseRun"""

    readable_id = serializers.CharField(source="text_id")
    course = serializers.SerializerMethodField()

    def get_course(self, instance):
        """Return a serialized version of the course"""
        return {"id": instance.course.id, "title": instance.course.title}

    class Meta:
        fields = [
            "id",
            "title",
            "start_date",
            "end_date",
            "course",
            "readable_id",
            "enrollment_start",
            "enrollment_end",
        ]
        model = CourseRun


class ProductContentObjectField(serializers.RelatedField):
    """Serializer field for related content objects"""

    def to_representation(self, value):
        """Serialize the content object using a serializer that matches the model type"""
        if isinstance(value, Program):
            return ProgramProductContentObjectSerializer(instance=value).data
        elif isinstance(value, CourseRun):
            return CourseRunProductContentObjectSerializer(instance=value).data
        raise Exception(  # noqa: TRY002
            "Unexpected to find type for Product.content_object:",  # noqa: EM101
            value.__class__,
        )


class ProgramRunSerializer(serializers.ModelSerializer):
    """Serializer for program runs"""

    class Meta:
        model = ProgramRun
        fields = ["id", "run_tag", "start_date", "end_date"]


class ProductSerializer(serializers.ModelSerializer):
    """Product Serializer with the latest ProductVersion also serialized"""

    product_type = serializers.CharField(source="content_type.model", read_only=True)
    content_object = ProductContentObjectField(read_only=True)
    latest_version = ProductVersionSerializer(read_only=True)

    class Meta:
        fields = [
            "id",
            "product_type",
            "is_private",
            "latest_version",
            "content_object",
        ]
        model = models.Product


class CouponSelectionSerializer(serializers.ModelSerializer):
    """CouponSelection serializer for viewing/updating coupons in basket"""

    code = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    targets = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()

    def get_code(self, instance):
        """Get the coupon code"""
        return instance.coupon.coupon_code

    def get_amount(self, instance):
        """Get the coupon discount amount"""
        # decimal fields should be represented as strings to prevent floating point parsing problems
        return str(latest_coupon_version(instance.coupon).payment_version.amount)

    def get_discount_type(self, instance):
        """Get the coupon discount type"""
        return latest_coupon_version(instance.coupon).payment_version.discount_type

    def get_targets(self, instance):
        """Get the product version id(s) in the basket the coupon applies to"""
        if instance.coupon.enabled and instance.coupon.is_global:
            eligible_product_ids = instance.basket.basketitems.values_list(
                "product", flat=True
            )
        else:
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
        fields = ["code", "amount", "targets", "discount_type"]
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
    tax_info = serializers.SerializerMethodField()

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
        serialized_product_version = FullProductVersionSerializer(
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
        """Get the basket items"""
        return [
            self._serialize_item(
                basket_item=item, basket=instance, context=self.context
            )
            for item in instance.basketitems.select_related("program_run").all()
        ]

    def get_coupons(self, instance):
        """Get the basket coupons"""
        return CouponSelectionSerializer(
            instance.couponselection_set.all(), many=True
        ).data

    def get_data_consents(self, instance):
        """Get the DataConsentUser objects associated with the basket via coupon and product"""
        data_consents = get_or_create_data_consent_users(instance)
        return DataConsentUserSerializer(instance=data_consents, many=True).data

    def get_tax_info(self, _):
        """Get the tax information for the current basket"""
        request = self.context.get("request", None)

        try:
            if request and hasattr(request, "user"):
                country_code = determine_visitor_country(request)
                if country_code is not None:
                    return (
                        TaxRate.objects.filter(active=True)
                        .get(country_code=country_code)
                        .to_dict()
                    )
            else:
                log.error("No request object in get_tax_info")
        except TaxRate.DoesNotExist:
            pass

        return TaxRate().to_dict()

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
                        "coupons": f"Enrollment / Promotional Code '{coupon_code}' is invalid"
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
    def _update_basket_data(  # noqa: PLR0913
        cls,
        basket,
        updated_product=None,
        updated_run_ids=None,
        program_run=None,
        should_update_program_run=False,  # noqa: FBT002
        coupon_version=None,
        data_consents=None,
        clear_all=False,  # noqa: FBT002
    ):
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
                update_dict = dict(quantity=1)  # noqa: C408
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
            (models.Product, courses.models.ProgramRun): The Product paired with an associated ProgramRun
                if one exists (or None if one does not exist)
        """
        item = items[0]
        request_product_id = item.get("product_id")
        try:
            product, product_content_obj, program_run = get_product_from_querystring_id(
                request_product_id
            )
            self._validate_internal_product(product_content_obj)

            if isinstance(product_content_obj, CourseRun):  # noqa: SIM102
                if (
                    product_content_obj.end_date
                    and product_content_obj.end_date < now_in_utc()
                ):
                    raise ValidationError(
                        "We're sorry, this course or program is no longer available for enrollment."  # noqa: EM101
                    )

        except (ObjectDoesNotExist, MultipleObjectsReturned) as exc:
            if isinstance(exc, MultipleObjectsReturned):
                log.error(  # noqa: TRY400
                    "Multiple Products found with identical ids: %s", request_product_id
                )
            raise ValidationError(
                {"items": f"Invalid product id {request_product_id}"}
            ) from exc
        return product, program_run

    def _validate_internal_product(self, product_content_obj):
        """
        Check if the product being bought is an external product, We don't sell external products

        Args:
            product_content_obj (Course, CourseRun, Program or ProgramRun): Ideally, there should only be
            CourseRun or Program but it could be either of those since we can add these as content types in products.
        """

        course_or_program = (
            getattr(product_content_obj, "course", None)
            or getattr(product_content_obj, "program", None)
            or product_content_obj
        )
        if course_or_program.is_external:
            raise ValidationError(
                "We're sorry, This product cannot be purchased on this web site."  # noqa: EM101
            )

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

    def update(self, instance, validated_data):
        items = validated_data.get("items")
        coupons = validated_data.get("coupons")
        data_consents = validated_data.get("data_consents")
        basket = instance

        self._validate_coupons(coupons)

        if items is None and coupons is None and data_consents is None:
            raise ValidationError("Invalid request")  # noqa: EM101

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
            raise ValidationError({"runs": "Some invalid courses were selected."})
        if len(set(product_run_course_map.values())) < len(run_ids):
            raise ValidationError({"runs": "Only one run per course can be selected"})

    def validate_items(self, items):
        """Validate some basic things about items"""
        if items:
            if len(items) > 1:
                raise ValidationError("Basket cannot contain more than one item")  # noqa: EM101
            item = items[0]
            product_id = item.get("product_id")
            if product_id is None:
                raise ValidationError("Invalid request")  # noqa: EM101
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
                    f"Invalid data consent id {','.join([str(consent_id) for consent_id in invalid_consent_ids])}"  # noqa: EM102
                )
        return {"data_consents": data_consents}

    class Meta:
        fields = ["items", "coupons", "data_consents", "tax_info"]
        model = models.Basket


class CouponPaymentSerializer(serializers.ModelSerializer):
    """Serializer for coupon payments"""

    class Meta:
        fields = "__all__"
        model = models.CouponPayment


class CouponPaymentVersionSerializer(serializers.ModelSerializer):
    """Serializer for coupon payment versions"""

    class Meta:
        fields = "__all__"
        model = models.CouponPaymentVersion


class CouponPaymentVersionDetailSerializer(serializers.ModelSerializer):
    """Serializer for coupon payment versions and related objects"""

    payment = CouponPaymentSerializer()
    company = CompanySerializer()

    class Meta:
        fields = "__all__"
        model = models.CouponPaymentVersion


class BaseCouponSerializer(serializers.Serializer):
    """Base serializer for coupon creation data"""

    name = serializers.CharField(
        max_length=256,
        validators=[UniqueValidator(queryset=models.CouponPayment.objects.all())],
    )
    tag = serializers.CharField(max_length=256, allow_null=True, required=False)
    amount = serializers.DecimalField(
        decimal_places=5,
        max_digits=20,
    )
    automatic = serializers.BooleanField(default=False)
    is_global = serializers.BooleanField(default=False)
    activation_date = serializers.DateTimeField()
    expiration_date = serializers.DateTimeField()
    product_ids = serializers.ListField(child=serializers.IntegerField())
    max_redemptions = serializers.IntegerField(default=1)
    max_redemptions_per_user = serializers.IntegerField(
        default=1,
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    coupon_type = serializers.ChoiceField(
        choices=set(
            zip(
                models.CouponPaymentVersion.COUPON_TYPES,
                models.CouponPaymentVersion.COUPON_TYPES,
            )
        )
    )
    discount_type = serializers.ChoiceField(
        choices=list(zip(DISCOUNT_TYPES, DISCOUNT_TYPES))
    )

    company = serializers.CharField(
        max_length=512, allow_null=True, allow_blank=True, required=False
    )
    include_future_runs = serializers.BooleanField()

    def validate(self, attrs):
        """Determine if product_ids was supplied or is_global was set"""
        # If neither of product_ids or is_global was set we need to bail
        error_message = validate_amount(attrs.get("discount_type"), attrs.get("amount"))
        if error_message:
            raise ValidationError({"discount": error_message})

        if (not attrs["product_ids"] or len(attrs["product_ids"]) == 0) and not attrs[
            "is_global"
        ]:
            raise ValidationError(
                {
                    "product_ids": "At least one product must be selected or coupon should be global."
                }
            )

        # If the data does not represent a coupon check for valid product_ids
        if not attrs["is_global"]:
            products_missing = set(attrs["product_ids"]) - set(
                models.Product.objects.filter(id__in=attrs["product_ids"]).values_list(
                    "id", flat=True
                )
            )
            if products_missing:
                raise ValidationError(
                    {
                        "product_ids": "Product with id(s) {} could not be found".format(
                            ",".join(str(pid) for pid in products_missing)
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        return create_coupons(
            company_id=validated_data.get("company"),
            tag=validated_data.get("tag"),
            name=validated_data.get("name"),
            automatic=validated_data.get("automatic", False),
            is_global=validated_data.get("is_global", False),
            activation_date=validated_data.get("activation_date"),
            expiration_date=validated_data.get("expiration_date"),
            amount=validated_data.get("amount"),
            num_coupon_codes=validated_data.get("num_coupon_codes"),
            coupon_type=validated_data.get("coupon_type"),
            discount_type=validated_data.get("discount_type"),
            max_redemptions=validated_data.get("max_redemptions", 1),
            max_redemptions_per_user=validated_data.get("max_redemptions_per_user", 1),
            payment_type=validated_data.get("payment_type"),
            payment_transaction=validated_data.get("payment_transaction"),
            coupon_code=validated_data.get("coupon_code"),
            product_ids=validated_data.get("product_ids"),
            include_future_runs=validated_data.get("include_future_runs"),
        )


class SingleUseCouponSerializer(BaseCouponSerializer):
    """Serializer for creating single-use coupons"""

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
    """Serializer for creating promo coupons"""

    num_coupon_codes = serializers.IntegerField(default=1, required=False)
    coupon_code = serializers.CharField(
        max_length=50,
        validators=[CouponUtils.validate_unique_coupon_code],
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


class PromoCouponDetailSerializer(serializers.ModelSerializer):
    """Serializer for getting promo coupons with eligibility information"""

    eligibility = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    activation_date = serializers.SerializerMethodField()
    expiration_date = serializers.SerializerMethodField()

    class Meta:
        model = models.Coupon
        fields = [
            "id",
            "coupon_code",
            "name",
            "activation_date",
            "expiration_date",
            "eligibility",
            "is_global",
        ]

    def get_eligibility(self, instance):
        """
        Get all CouponEligibility records related to the coupons created by this CouponPayment.
        """
        eligibility_qs = instance.couponeligibility_set.all()

        return [
            {
                "coupon_code": instance.coupon_code,
                "product_id": eligibility.product.id,
                "program_run_id": eligibility.program_run.id
                if eligibility.program_run
                else None,
            }
            for eligibility in eligibility_qs
        ]

    def get_name(self, instance):
        """Get the 'name' property of the associated CouponPayment"""
        return instance.payment.name

    def get_activation_date(self, instance):
        """Get the activation date of the associated CouponPayment"""
        return instance.payment.latest_version.activation_date

    def get_expiration_date(self, instance):
        """Get the expiration date of the associated CouponPayment"""
        return instance.payment.latest_version.expiration_date


class PromoCouponUpdateSerializer(serializers.Serializer):
    """Serializer for updating promo coupons"""

    promo_coupon = serializers.IntegerField()
    is_global = serializers.BooleanField(default=False)
    activation_date = serializers.DateTimeField()
    expiration_date = serializers.DateTimeField()
    product_ids = serializers.ListField(child=serializers.IntegerField())

    def validate_promo_coupon(self, value):
        """Validate that the promo coupon exists"""
        try:
            return models.Coupon.objects.get(id=value)
        except models.Coupon.DoesNotExist:
            raise serializers.ValidationError("Coupon not found.")

    def validate_product_ids(self, value):
        """Validate that the product ids exist"""
        products = list(models.Product.objects.filter(id__in=value))
        if len(products) != len(set(value)):
            raise serializers.ValidationError("Some products not found.")
        return products

    def validate(self, data):
        """Validate the product_ids are empty when is_global is True"""
        is_global = data.get("is_global", False)
        product_ids = data.get("product_ids", [])

        if is_global and product_ids:
            raise serializers.ValidationError(
                {"product_ids": "Must be empty when is_global is true."}
            )
        if not is_global and not product_ids:
            raise serializers.ValidationError(
                {"product_ids": "This field is required when is_global is false."}
            )
        return data

    @transaction.atomic
    def save(self):
        """Save the updated promo coupon data."""
        coupon = self.validated_data["promo_coupon"]
        is_global = self.validated_data["is_global"]
        activation_date = self.validated_data["activation_date"]
        expiration_date = self.validated_data["expiration_date"]
        products = self.validated_data["product_ids"]

        coupon_payment_version = coupon.payment.latest_version
        coupon_payment_version.pk = None
        coupon_payment_version.activation_date = activation_date
        coupon_payment_version.expiration_date = expiration_date
        coupon_payment_version.save()

        models.CouponVersion.objects.create(
            coupon=coupon,
            payment_version=coupon_payment_version,
        )

        # Replace eligibilities
        coupon.couponeligibility_set.all().delete()
        models.CouponEligibility.objects.bulk_create(
            [
                models.CouponEligibility(product=product, coupon=coupon)
                for product in products
            ]
        )

        # Update coupon is_global
        coupon.is_global = is_global
        coupon.save()

        return coupon


class DataConsentUserSerializer(serializers.ModelSerializer):
    """Serializer for DataConsentUsers"""

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
    """Summary serializer for Line model"""

    product_version = BaseProductVersionSerializer()

    class Meta:
        model = models.Line
        fields = ["product_version", "quantity"]


class OrderReceiptSerializer(serializers.ModelSerializer):
    """Serializer for extracting receipt info from an Order object"""

    lines = serializers.SerializerMethodField()
    purchaser = serializers.SerializerMethodField()
    coupon = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    receipt = serializers.SerializerMethodField()

    def get_receipt(self, instance):
        """Get receipt information if it exists"""
        receipt = instance.receipt_set.order_by("-created_on").first()
        if receipt:
            data = {
                "card_number": None,
                "card_type": None,
                "name": None,
                "bill_to_email": None,
                "payment_method": None,
            }

            if "req_card_number" in receipt.data:
                data["card_number"] = receipt.data["req_card_number"]
            if (
                "req_card_type" in receipt.data
                and receipt.data["req_card_type"] in CYBERSOURCE_CARD_TYPES
            ):
                data["card_type"] = CYBERSOURCE_CARD_TYPES[
                    receipt.data["req_card_type"]
                ]
            if "req_payment_method" in receipt.data:
                data["payment_method"] = receipt.data["req_payment_method"]
            if "req_bill_to_email" in receipt.data:
                data["bill_to_email"] = receipt.data["req_bill_to_email"]
            if (
                "req_bill_to_forename" in receipt.data
                or "req_bill_to_surname" in receipt.data
            ):
                data["name"] = (
                    f"{receipt.data.get('req_bill_to_forename')} {receipt.data.get('req_bill_to_surname')}"
                )
            return data
        return None

    def get_lines(self, instance):
        """Get product information along with applied discounts"""
        coupon_redemption = instance.couponredemption_set.first()
        lines = []
        for line in instance.lines.all():
            coupon_version = (
                coupon_redemption.coupon_version if coupon_redemption else None
            )
            product_price_and_tax = get_product_version_price_with_discount_tax(
                coupon_version=coupon_version,
                product_version=line.product_version,
                tax_rate=instance.tax_rate,
            )
            tax_paid = Decimal(
                product_price_and_tax["tax_assessed"] * line.quantity
            ).quantize(Decimal(".01"))
            total_price = product_price_and_tax["price"] * line.quantity
            total_paid = Decimal(total_price + tax_paid).quantize(Decimal(".01"))
            discount = (line.product_version.price * line.quantity) - total_price
            total_before_tax = Decimal(total_paid - tax_paid).quantize(Decimal(".01"))
            dates = CourseRunEnrollment.objects.filter(
                order_id=instance.id, change_status__isnull=True
            ).aggregate(
                start_date=dj_models.Min("run__start_date"),
                end_date=dj_models.Max("run__end_date"),
            )

            content_object = line.product_version.product.content_object
            (course, program, certificate_page, CEUs) = (None, None, None, None)
            if isinstance(content_object, Program):
                program = Program.objects.get(readable_id=line.product_version.text_id)
            elif isinstance(content_object, CourseRun):
                course = Course.objects.get(
                    courseruns__courseware_id=line.product_version.text_id
                )
            if course and course.page and course.page.certificate_page:
                certificate_page = course.page.certificate_page
            elif program and program.page and program.page.certificate_page:
                certificate_page = program.page.certificate_page

            if certificate_page:
                CEUs = certificate_page.CEUs
                for override in certificate_page.overrides:
                    if (
                        override.value.get("readable_id")
                        == line.product_version.text_id
                    ):
                        CEUs = override.value.get("CEUs")
                        break
            lines.append(
                dict(
                    quantity=line.quantity,
                    total_paid=str(total_paid),
                    tax_paid=str(tax_paid),
                    discount=str(discount),
                    total_before_tax=str(total_before_tax),
                    CEUs=CEUs if CEUs else None,
                    **BaseProductVersionSerializer(line.product_version).data,
                    start_date=dates["start_date"],
                    end_date=dates["end_date"],
                )
            )
        return lines

    def get_order(self, instance):
        """Get order-specific information"""
        return dict(  # noqa: C408
            id=instance.id,
            created_on=instance.created_on,
            reference_number=instance.reference_number,
            tax_rate=instance.tax_rate,
            tax_rate_name=instance.tax_rate_name,
            tax_country_code=instance.tax_country_code,
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
