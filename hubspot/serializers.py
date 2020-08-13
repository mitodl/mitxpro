""" Serializers for HubSpot"""
import re

from rest_framework import serializers

from b2b_ecommerce import models as b2b_models
from ecommerce import models
from ecommerce.api import get_product_version_price_with_discount, round_half_up
from ecommerce.models import CouponVersion, ProductVersion, CouponRedemption
from hubspot.api import format_hubspot_id
from users.models import User

ORDER_STATUS_MAPPING = {
    models.Order.FULFILLED: "processed",
    models.Order.FAILED: "checkout_completed",
    models.Order.CREATED: "checkout_completed",
    models.Order.REFUNDED: "processed",
}

ORDER_TYPE_B2B = "B2B"
ORDER_TYPE_B2C = "B2C"


class LineSerializer(serializers.ModelSerializer):
    """ Line Serializer for Hubspot """

    product = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()

    def get_order(self, instance):
        """ Get the order id and return the hubspot deal integratorObject id"""
        return format_hubspot_id(instance.order.id)

    def get_product(self, instance):
        """ Get the product id and return the hubspot product integratorObject id"""
        return format_hubspot_id(instance.product_version.product.id)

    def get_status(self, instance):
        """ Get status of the associated Order """
        return instance.order.status

    def get_product_id(self, instance):
        """Return the product version text_id"""
        if instance.product_version:
            return instance.product_version.text_id
        return ""

    class Meta:
        fields = ("id", "product", "order", "quantity", "status", "product_id")
        model = models.Line


class B2BProductVersionToLineSerializer(serializers.ModelSerializer):
    """ B2B product version to line serializer for Hubspot """

    id = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()

    def get_id(self, instance):
        """ Get the product version id"""
        return format_hubspot_id(instance.product_version.id)

    def get_product(self, instance):
        """ Get the product id and return the hubspot product integratorObject id"""
        return format_hubspot_id(instance.product_version.product.id)

    def get_order(self, instance):
        """ Get the order id and return the hubspot deal integratorObject id"""
        return format_hubspot_id(instance.integration_id)

    def get_quantity(self, instance):
        """return the number of seats associated with the b2b order"""
        return instance.num_seats

    def get_status(self, instance):
        """ Get status of the associated Order """
        return instance.status

    def get_product_id(self, instance):
        """Return the product version text_id"""
        if instance.product_version:
            return instance.product_version.text_id
        return ""

    class Meta:
        fields = ("id", "product", "order", "quantity", "status", "product_id")
        model = b2b_models.B2BOrder


class B2BOrderToDealSerializer(serializers.ModelSerializer):
    """ B2BOrder/Deal Serializer for Hubspot """

    name = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    close_date = serializers.SerializerMethodField(allow_null=True)
    amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField(allow_null=True)
    company = serializers.SerializerMethodField(allow_null=True)
    payment_type = serializers.SerializerMethodField(allow_null=True)
    payment_transaction = serializers.SerializerMethodField(allow_null=True)
    purchaser = serializers.SerializerMethodField(allow_null=True)

    def get_name(self, instance):
        """ Return the order/deal name """
        return f"XPRO-B2BORDER-{instance.id}"

    def get_stage(self, instance):
        """ Return the status mapped to the hubspot equivalent """
        return ORDER_STATUS_MAPPING[instance.status]

    def get_close_date(self, instance):
        """ Return the updated_on date (as a timestamp in milliseconds) if fulfilled """
        if instance.status == b2b_models.B2BOrder.FULFILLED:
            return int(instance.updated_on.timestamp() * 1000)

    def get_amount(self, instance):
        """ Get the amount paid after discount """
        return (instance.total_price).to_eng_string()

    def get_discount_amount(self, instance):
        """ Get the discount amount if any """
        if instance.discount:
            return round_half_up(instance.discount).to_eng_string()

    def get_discount_percent(self, instance):
        """ Get the discount percentage if any """
        if instance.coupon:
            return round_half_up(instance.coupon.discount_percent * 100).to_eng_string()

    def get_company(self, instance):
        """ Get the company id if any """
        if instance.coupon:
            company = instance.coupon.company
            if company:
                return company.name

    def get_coupon_code(self, instance):
        """ Get the coupon code used for the order if any """
        if instance.coupon:
            return instance.coupon.coupon_code

    def get_payment_type(self, instance):
        """Get the payment type"""
        if instance.coupon_payment_version:
            payment_type = instance.coupon_payment_version.payment_type
            if payment_type:
                return payment_type

    def get_payment_transaction(self, instance):
        """Get the payment transaction id if any"""
        if instance.coupon_payment_version:
            payment_transaction = instance.coupon_payment_version.payment_transaction
            if payment_transaction:
                return payment_transaction

    def get_purchaser(self, instance):
        """Get the purchaser id"""
        if instance.email:
            existing_user = User.objects.filter(email=instance.email).first()
            user_id = existing_user.id if existing_user else instance.email
            return format_hubspot_id(user_id)

    class Meta:
        fields = (
            "id",
            "name",
            "amount",
            "stage",
            "status",
            "discount_amount",
            "discount_percent",
            "close_date",
            "coupon_code",
            "num_seats",
            "company",
            "payment_type",
            "payment_transaction",
            "purchaser",
        )
        model = b2b_models.B2BOrder


class OrderToDealSerializer(serializers.ModelSerializer):
    """ Order/Deal Serializer for Hubspot """

    name = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    close_date = serializers.SerializerMethodField(allow_null=True)
    amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField(allow_null=True)
    company = serializers.SerializerMethodField(allow_null=True)
    lines = LineSerializer(many=True)
    purchaser = serializers.SerializerMethodField()
    order_type = serializers.SerializerMethodField()
    payment_type = serializers.SerializerMethodField(allow_null=True)
    payment_transaction = serializers.SerializerMethodField(allow_null=True)

    _coupon_version = None
    _product_version = None

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

    def get_name(self, instance):
        """ Return the order/deal name """
        return f"XPRO-ORDER-{instance.id}"

    def get_stage(self, instance):
        """ Return the status mapped to the hubspot equivalent """
        return ORDER_STATUS_MAPPING[instance.status]

    def get_close_date(self, instance):
        """ Return the updated_on date (as a timestamp in milliseconds) if fulfilled """
        if instance.status == models.Order.FULFILLED:
            return int(instance.updated_on.timestamp() * 1000)

    def get_amount(self, instance):
        """ Get the amount paid after discount """
        return get_product_version_price_with_discount(
            coupon_version=self._get_coupon_version(instance),
            product_version=self._get_product_version(instance),
        ).to_eng_string()

    def get_discount_amount(self, instance):
        """ Get the discount amount if any """

        coupon_version = self._get_coupon_version(instance)
        if not coupon_version:
            return "0.0000"

        return round_half_up(
            coupon_version.payment_version.amount
            * self._get_product_version(instance).price
        ).to_eng_string()

    def get_discount_percent(self, instance):
        """ Get the discount percentage if any """

        coupon_version = self._get_coupon_version(instance)
        if not coupon_version:
            return "0"

        return (coupon_version.payment_version.amount * 100).to_eng_string()

    def get_company(self, instance):
        """ Get the company id if any """
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            company = coupon_version.payment_version.company
            if company:
                return company.name

    def get_payment_type(self, instance):
        """Get the payment type"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            payment_type = coupon_version.payment_version.payment_type
            if payment_type:
                return payment_type

    def get_payment_transaction(self, instance):
        """Get the payment transaction id if any"""
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            payment_transaction = coupon_version.payment_version.payment_transaction
            if payment_transaction:
                return payment_transaction

    def get_coupon_code(self, instance):
        """ Get the coupon code used for the order if any """
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            return coupon_version.coupon.coupon_code

    def get_order_type(self, instance):
        """ Determine if this is a B2B or B2C order """
        coupon_version = self._get_coupon_version(instance)
        if coupon_version:
            company = coupon_version.payment_version.company
            transaction_id = coupon_version.payment_version.payment_transaction
            if company or transaction_id:
                return ORDER_TYPE_B2B
        return ORDER_TYPE_B2C

    def get_purchaser(self, instance):
        """ Get the Hubspot ID for the purchaser"""
        return format_hubspot_id(instance.purchaser.id)

    class Meta:
        fields = (
            "id",
            "name",
            "amount",
            "stage",
            "status",
            "discount_amount",
            "discount_percent",
            "close_date",
            "coupon_code",
            "lines",
            "purchaser",
            "company",
            "order_type",
            "payment_type",
            "payment_transaction",
        )
        model = models.Order


class ProductSerializer(serializers.ModelSerializer):
    """ Product Serializer for Hubspot """

    title = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_title(self, instance):
        """ Return the product title and Courserun number or ProductVersion text_id"""
        product_obj = instance.content_type.get_object_for_this_type(
            pk=instance.object_id
        )
        title_run_id = re.findall(r"\+R(\d+)$", product_obj.text_id)
        title_suffix = f"Run {title_run_id[0]}" if title_run_id else product_obj.text_id
        return f"{product_obj.title}: {title_suffix}"

    def get_product_type(self, instance):
        """ Return the product type """
        return instance.content_type.model

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
        fields = "__all__"
        model = models.Product
