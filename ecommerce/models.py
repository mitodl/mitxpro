"""Models for ecommerce"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models

from mitxpro.models import AuditableModel, AuditModel, TimestampedModel


class Product(TimestampedModel):
    """
    Representation of a purchasable product. There is a GenericForeignKey to a CourseRun, Course, or Program.
    Other about the product like price is stored in ProductVersion.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        help_text="content_object is a link to either a Course, CourseRun, or a Program",
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("content_type", "object_id")

    def __str__(self):
        """Description of a product"""
        return f"Product for {self.content_object}"


class ProductVersion(TimestampedModel):
    """
    An append-only table for Product, storing information that might be
    updated in the future like price or description.
    """

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="productversions"
    )
    price = models.DecimalField(decimal_places=2, max_digits=20)
    description = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        """Description of a ProductVersion"""
        return f"ProductVersion for {self.description}, ${self.price}"


class Basket(TimestampedModel):
    """
    Represents a User's basket. A Basket is made up of BasketItems. Each Basket is assigned to one user and
    it is reused for each checkout.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        """Description of Basket"""
        return f"Basket for {self.user}"


class BasketItem(TimestampedModel):
    """
    Represents one or more products in a user's basket.
    """

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    basket = models.ForeignKey(
        Basket, on_delete=models.PROTECT, related_name="basketitems"
    )
    quantity = models.PositiveIntegerField()

    def __str__(self):
        """Description of BasketItem"""
        return f"BasketItem of product {self.product} (qty: {self.quantity}"


class Order(TimestampedModel, AuditableModel):
    """
    An order containing information for a purchase. Orders which are fulfilled represent successful
    completion of a purchase and are the source of truth for this information.
    """

    FULFILLED = "fulfilled"
    FAILED = "failed"
    CREATED = "created"
    REFUNDED = "refunded"

    STATUSES = [CREATED, FULFILLED, FAILED, REFUNDED]
    FULFILLED_STATUSES = [FULFILLED]

    purchaser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        choices=[(status, status) for status in STATUSES],
        default=CREATED,
        max_length=30,
        db_index=True,
    )

    def __str__(self):
        """Description for Order"""
        return f"Order #{self.id}, status={self.status}"

    @classmethod
    def get_audit_class(cls):
        return OrderAudit

    def to_dict(self):
        """
        Get a serialized representation of the Order and any attached Basket and Lines
        """
        raise NotImplementedError


class OrderAudit(AuditModel):
    """
    Audit model for Order. This table is only meant for recordkeeping purposes. The serialized
    orders will also include information from any related tables.
    """

    order = models.ForeignKey(Order, null=True, on_delete=models.PROTECT)

    @classmethod
    def get_related_field_name(cls):
        return "order"


class Line(TimestampedModel):
    """
    A line in an Order. This contains information about a specific item which is purchased.
    """

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lines")
    product_version = models.ForeignKey(ProductVersion, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        """Description for Line"""
        return f"Line for order #{self.order.id}, {self.quantity} {self.product_version}(s)"


class CouponInvoice(TimestampedModel):
    """
    Information about creation of one or more coupons. Most information will go in CouponInvoiceVersion.
    tag should be a string which never changes and is unique for the coupon invoice.
    """

    tag = models.TextField(unique=True)

    def __str__(self):
        """Description for CouponInvoice"""
        return f"CouponInvoice {self.tag}"


class CouponInvoiceVersion(TimestampedModel):
    """
    An append-only table for CouponInvoice information. Invoice information is stored here and the latest version
    for a particular invoice is the source of truth for this information.
    """

    PROMO = "promo"
    SINGLE_USE = "single-use"

    COUPON_TYPES = [PROMO, SINGLE_USE]

    invoice = models.ForeignKey(CouponInvoice, on_delete=models.PROTECT)

    coupon_type = models.CharField(
        choices=[(_type, _type) for _type in COUPON_TYPES], max_length=30
    )
    num_coupon_codes = models.PositiveIntegerField()
    max_redemptions = models.PositiveIntegerField()
    max_redemptions_per_user = models.PositiveIntegerField()
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        help_text="Percent discount for a coupon. Between 0 and 1.",
    )
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable after this time",
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable before this time",
    )

    class Meta:
        indexes = [models.Index(fields=["created_on"])]

    def __str__(self):
        """Description for CouponInvoiceVersion"""
        return f"CouponInvoiceVersion for {self.num_coupon_codes} of type {self.coupon_type}"


class Coupon(TimestampedModel):
    """
    Represents a coupon with a code. The latest CouponVersion for this instance is the source of truth for
    coupon information. Since the coupon_code is the identifier for the coupon, this should never be changed.
    """

    coupon_code = models.CharField(max_length=50)
    invoice = models.ForeignKey(CouponInvoice, on_delete=models.PROTECT)

    def __str__(self):
        """Description for Coupon"""
        return f"Coupon {self.coupon_code} for {self.invoice}"


class CouponVersion(TimestampedModel):
    """
    An append-only table for coupon codes. This should contain any mutable information specific to a coupon
    (at the moment this is only a link to a corresponding CouponInvoiceVersion).
    """

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    invoice_version = models.ForeignKey(CouponInvoiceVersion, on_delete=models.PROTECT)

    def __str__(self):
        """Description for CouponVersion"""
        return f"CouponVersion {self.coupon.coupon_code} for {self.invoice_version}"


class CouponEligibility(TimestampedModel):
    """
    A link from a coupon to product which the coupon would apply to. There may be many coupons
    which could apply to a product, or a coupon can be valid for many different products.
    """

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    def __str__(self):
        """Description of CouponProduct"""
        return f"CouponProduct for product {self.product}, coupon {self.coupon}"


class CouponSelection(TimestampedModel):
    """
    A link from a Coupon to a Basket the coupon is being used with. At the moment there should only be one
    coupon per basket but this is a many to many table for future flexibility.
    """

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT)
    basket = models.ForeignKey(Basket, on_delete=models.PROTECT)

    def __str__(self):
        """Description of CouponSelection"""
        return f"CouponSelection for basket {self.basket}, coupon {self.coupon}"


class CouponRedemption(TimestampedModel):
    """
    A link from a CouponVersion to an Order. This indicates that a coupon has been used (if the order is fulfilled)
    or that it is intended to be used soon.
    """

    coupon_version = models.ForeignKey(CouponVersion, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)

    def __str__(self):
        """Description of CouponRedemption"""
        return f"CouponRedemption for order {self.order}, coupon version {self.coupon_version}"


class Receipt(TimestampedModel):
    """
    The contents of the message from CyberSource about an Order fulfillment or cancellation. The order
    should always exist but it's nullable in case there is a problem matching the CyberSource response to the order.
    """

    order = models.ForeignKey(Order, null=True, on_delete=models.PROTECT)
    data = JSONField()

    def __str__(self):
        """Description of Receipt"""
        if self.order:
            return f"Receipt for order {self.order.id}"
        else:
            return "Receipt with no attached order"
