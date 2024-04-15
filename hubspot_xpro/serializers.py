"""Serializers for HubSpot"""
from django.conf import settings
from mitol.hubspot_api.api import format_app_id
from rest_framework import serializers

from b2b_ecommerce import models as b2b_models
from b2b_ecommerce.constants import B2B_ORDER_PREFIX
from ecommerce import models
from ecommerce.api import get_product_version_price_with_discount, round_half_up
from ecommerce.constants import DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.models import CouponRedemption, CouponVersion, ProductVersion
from hubspot_xpro.api import format_product_name, get_hubspot_id_for_object

ORDER_STATUS_MAPPING = {
    models.Order.FULFILLED: "processed",
    models.Order.FAILED: "checkout_completed",
    models.Order.CREATED: "checkout_completed",
    models.Order.REFUNDED: "processed",
}

ORDER_TYPE_B2B = "B2B"
ORDER_TYPE_B2C = "B2C"


class LineSerializer(serializers.ModelSerializer):
    """Line Serializer for Hubspot"""

    unique_app_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    hs_product_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    def get_unique_app_id(self, instance):
        """Get the app_id for the object"""
        return format_app_id(instance.id)

    def get_name(self, instance):
        """Get the product version name"""
        if instance.product_version:
            return format_product_name(instance.product_version.product)
        return ""

    def get_hs_product_id(self, instance):
        """Return the hubspot id for the product"""
        if not instance.product_version:
            return None
        return get_hubspot_id_for_object(instance.product_version.product)

    def get_status(self, instance):
        """Get status of the associated Order"""
        return instance.order.status

    def get_product_id(self, instance):
        """Return the product version text_id"""
        return instance.product_version.text_id

    def get_price(self, instance):
        """Get the product version price"""
        return instance.product_version.price.to_eng_string()

    class Meta:
        fields = (
            "unique_app_id",
            "name",
            "hs_product_id",
            "quantity",
            "status",
            "product_id",
            "price",
        )
        model = models.Line


class B2BOrderToLineItemSerializer(serializers.ModelSerializer):
    """B2B product version to line serializer for Hubspot"""

    unique_app_id = serializers.SerializerMethodField()
    hs_product_id = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    def get_unique_app_id(self, instance):
        """Get the app_id for the object"""
        return (
            f"{settings.MITOL_HUBSPOT_API_ID_PREFIX}-{B2B_ORDER_PREFIX}-{instance.id}"
        )

    def get_quantity(self, instance):
        """Return the number of seats associated with the b2b order"""
        return instance.num_seats

    def get_status(self, instance):
        """Get status of the associated Order"""
        return instance.status

    def get_hs_product_id(self, instance):
        """Get the hubspot id of the product"""
        return get_hubspot_id_for_object(instance.product_version.product)

    def get_product_id(self, instance):
        """Return the product version text_id"""
        if instance.product_version:
            return instance.product_version.text_id
        return ""

    def get_price(self, instance):
        """Get the product version price"""
        return instance.product_version.price.to_eng_string()

    def get_name(self, instance):
        """Get the product name"""
        if instance.product_version:
            return format_product_name(instance.product_version.product)
        return ""

    class Meta:
        fields = (
            "unique_app_id",
            "hs_product_id",
            "quantity",
            "status",
            "price",
            "product_id",
            "name",
        )
        model = b2b_models.B2BOrder


class B2BOrderToDealSerializer(serializers.ModelSerializer):
    """B2BOrder/Deal Serializer for Hubspot"""

    unique_app_id = serializers.SerializerMethodField()
    dealname = serializers.SerializerMethodField()
    dealstage = serializers.SerializerMethodField()
    closedate = serializers.SerializerMethodField(allow_null=True)
    amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField(allow_null=True)
    company = serializers.SerializerMethodField(allow_null=True)
    payment_type = serializers.SerializerMethodField(allow_null=True)
    payment_transaction = serializers.SerializerMethodField(allow_null=True)
    pipeline = serializers.ReadOnlyField(default=settings.HUBSPOT_PIPELINE_ID)
    order_type = serializers.ReadOnlyField(default=ORDER_TYPE_B2B)

    def get_unique_app_id(self, instance):
        """Get the app_id for the object"""
        return (
            f"{settings.MITOL_HUBSPOT_API_ID_PREFIX}-{B2B_ORDER_PREFIX}-{instance.id}"
        )

    def get_dealname(self, instance):
        """Return the order/deal name"""
        return f"{B2B_ORDER_PREFIX}-{instance.id}"

    def get_dealstage(self, instance):
        """Return the status mapped to the hubspot_xpro equivalent"""
        return ORDER_STATUS_MAPPING[instance.status]

    def get_closedate(self, instance):
        """Return the updated_on date (as a timestamp in milliseconds) if fulfilled"""
        if instance.status == b2b_models.B2BOrder.FULFILLED:  # noqa: RET503
            return int(instance.updated_on.timestamp() * 1000)

    def get_amount(self, instance):
        """Get the amount paid after discount"""
        return (instance.total_price).to_eng_string()

    def get_discount_amount(self, instance):
        """Get the discount amount if any"""
        if instance.discount:  # noqa: RET503
            return round_half_up(instance.discount).to_eng_string()

    def get_discount_percent(self, instance):
        """Get the discount percentage if any"""
        if instance.coupon:  # noqa: RET503
            return round_half_up(instance.coupon.discount_percent * 100).to_eng_string()

    def get_discount_type(self, instance):
        """We are only supporting percent-off for b2b as of now"""
        if instance.coupon:  # noqa: RET503
            return DISCOUNT_TYPE_PERCENT_OFF

    def get_company(self, instance):
        """Get the company id if any"""
        if instance.coupon:  # noqa: RET503
            company = instance.coupon.company
            if company:  # noqa: RET503
                return company.name

    def get_coupon_code(self, instance):
        """Get the coupon code used for the order if any"""
        if instance.coupon:  # noqa: RET503
            return instance.coupon.coupon_code

    def get_payment_type(self, instance):
        """Get the payment type"""
        if instance.coupon_payment_version:  # noqa: RET503
            payment_type = instance.coupon_payment_version.payment_type
            if payment_type:  # noqa: RET503
                return payment_type

    def get_payment_transaction(self, instance):
        """Get the payment transaction id if any"""
        if instance.coupon_payment_version:  # noqa: RET503
            payment_transaction = instance.coupon_payment_version.payment_transaction
            if payment_transaction:  # noqa: RET503
                return payment_transaction

    class Meta:
        fields = (
            "unique_app_id",
            "dealname",
            "amount",
            "dealstage",
            "status",
            "discount_amount",
            "discount_percent",
            "discount_type",
            "closedate",
            "coupon_code",
            "num_seats",
            "company",
            "order_type",
            "payment_type",
            "payment_transaction",
            "pipeline",
        )
        model = b2b_models.B2BOrder


class OrderToDealSerializer(serializers.ModelSerializer):
    """Order/Deal Serializer for Hubspot"""

    unique_app_id = serializers.SerializerMethodField()
    dealname = serializers.SerializerMethodField()
    dealstage = serializers.SerializerMethodField()
    closedate = serializers.SerializerMethodField(allow_null=True)
    amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField(allow_null=True)
    company = serializers.SerializerMethodField(allow_null=True)
    order_type = serializers.SerializerMethodField()
    payment_type = serializers.SerializerMethodField(allow_null=True)
    payment_transaction = serializers.SerializerMethodField(allow_null=True)
    pipeline = serializers.ReadOnlyField(default=settings.HUBSPOT_PIPELINE_ID)

    _coupon_version = None
    _product_version = None

    def get_unique_app_id(self, instance):
        """Get the app_id for the object"""
        return format_app_id(instance.id)

    def _get_coupon_version(self, instance):
        """Return the order coupon version"""
        if self._coupon_version is None:
            self._coupon_version = CouponVersion.objects.filter(
                couponredemption__order=instance
            ).first()
        return self._coupon_version

    def _get_product_version(self, instance):
        """Return the order product version"""
        if self._product_version is None:
            self._product_version = ProductVersion.objects.filter(
                id__in=instance.lines.values_list("product_version", flat=True)
            ).first()
        return self._product_version

    def _get_redemption(self, instance):
        """Return the order coupon redemption"""
        return CouponRedemption.objects.filter(order=instance).first()

    def get_dealname(self, instance):
        """Return the order/deal name"""
        return f"XPRO-ORDER-{instance.id}"

    def get_dealstage(self, instance):
        """Return the status mapped to the hubspot_xpro equivalent"""
        return ORDER_STATUS_MAPPING[instance.status]

    def get_closedate(self, instance):
        """Return the updated_on date (as a timestamp in milliseconds) if fulfilled"""
        if instance.status == models.Order.FULFILLED:  # noqa: RET503
            return int(instance.updated_on.timestamp() * 1000)

    def get_discount_type(self, instance):
        """Get the discount type of the applied coupon"""

        coupon_version = self._get_coupon_version(instance)
        if coupon_version:  # noqa: RET503
            return coupon_version.payment_version.discount_type

    def get_amount(self, instance):
        """Get the amount paid after discount"""
        return get_product_version_price_with_discount(
            coupon_version=self._get_coupon_version(instance),
            product_version=self._get_product_version(instance),
        ).to_eng_string()

    def get_discount_amount(self, instance):
        """Get the discount amount if any"""
        coupon_version = self._get_coupon_version(instance)
        if not coupon_version:
            return "0.0000"

        payment_version = coupon_version.payment_version
        discount_amount = payment_version.calculate_discount_amount(
            price=self._get_product_version(instance).price
        )
        return discount_amount.to_eng_string()

    def get_discount_percent(self, instance):
        """Get the discount percentage if any"""
        coupon_version = self._get_coupon_version(instance)
        if not coupon_version:
            return "0"

        payment_version = coupon_version.payment_version
        discount_percent = payment_version.calculate_discount_percent(
            price=self._get_product_version(instance).price
        )
        return discount_percent.to_eng_string()

    def get_company(self, instance):
        """Get the company id if any"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:  # noqa: RET503
            company = coupon_version.payment_version.company
            if company:  # noqa: RET503
                return company.name

    def get_payment_type(self, instance):
        """Get the payment type"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:  # noqa: RET503
            payment_type = coupon_version.payment_version.payment_type
            if payment_type:  # noqa: RET503
                return payment_type

    def get_payment_transaction(self, instance):
        """Get the payment transaction id if any"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:  # noqa: RET503
            payment_transaction = coupon_version.payment_version.payment_transaction
            if payment_transaction:  # noqa: RET503
                return payment_transaction

    def get_coupon_code(self, instance):
        """Get the coupon code used for the order if any"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:  # noqa: RET503
            return coupon_version.coupon.coupon_code

    def get_order_type(self, instance):
        """Determine if this is a B2B or B2C order"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            company = coupon_version.payment_version.company
            transaction_id = coupon_version.payment_version.payment_transaction
            if company or transaction_id:
                return ORDER_TYPE_B2B
        return ORDER_TYPE_B2C

    class Meta:
        fields = (
            "unique_app_id",
            "dealname",
            "amount",
            "dealstage",
            "status",
            "discount_amount",
            "discount_percent",
            "discount_type",
            "closedate",
            "coupon_code",
            "company",
            "order_type",
            "payment_type",
            "payment_transaction",
            "pipeline",
        )
        model = models.Order


class ProductSerializer(serializers.ModelSerializer):
    """Product Serializer for Hubspot"""

    unique_app_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_unique_app_id(self, instance):
        """Get the app_id for the object"""
        return format_app_id(instance.id)

    def get_name(self, instance):
        """Return the product title and Courserun number or ProductVersion text_id"""
        return format_product_name(instance)

    def get_price(self, instance):
        """Return the latest product version price"""
        product_version = instance.latest_version
        if product_version:
            return product_version.price.to_eng_string()
        return "0.00"

    def get_description(self, instance):
        """Return the latest product version description"""
        product_version = instance.latest_version
        if product_version:
            return product_version.description
        return ""

    class Meta:
        fields = ["unique_app_id", "name", "price", "description"]
        read_only_fields = fields
        model = models.Product


def get_hubspot_serializer(obj: object) -> serializers.ModelSerializer:
    """Get the appropriate serializer for an object"""
    if isinstance(obj, b2b_models.B2BOrder):
        serializer_class = B2BOrderToDealSerializer
    elif isinstance(obj, models.Order):
        serializer_class = OrderToDealSerializer
    elif isinstance(obj, b2b_models.B2BLine):
        serializer_class = B2BOrderToLineItemSerializer
        # B2BLine is a special case, needs to be based of parent B2BOrder
        return serializer_class(obj.order)
    elif isinstance(obj, models.Line):
        serializer_class = LineSerializer
    elif isinstance(obj, models.Product):
        serializer_class = ProductSerializer
    else:
        raise NotImplementedError("Not a supported class")  # noqa: EM101
    return serializer_class(obj)
