"""Models for business to business ecommerce"""
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from b2b_ecommerce.constants import REFERENCE_NUMBER_PREFIX
from ecommerce.models import (
    Company,
    CouponPaymentVersion,
    Product,
    ProductVersion,
    OrderAbstract,
    OrderManager,
)
from mitxpro.models import AuditModel, AuditableModel, TimestampedModel
from mitxpro.utils import serialize_model_object

B2B_INTEGRATION_PREFIX = "B2B-"


class B2BCouponManager(models.Manager):
    """
    Add a function to filter valid coupons
    """

    def get_unexpired_coupon(self, *, coupon_code, product_id):
        """
        Returns an an unexpired coupon with the coupon code for that product. Otherwise raise B2BCoupon.DoesNotExist.

        Args:
            coupon_code (str): The coupon code for the B2BCoupon
            product_id (int): The primary key for the Product

        Returns:
            B2BCoupon:
                The coupon instance. If no coupon is found a B2BCoupon.DoesNotExist error is raised
        """
        coupon = (
            self.filter(
                Q(coupon_code=coupon_code),
                Q(enabled=True),
                Q(product_id=None) | Q(product_id=product_id),
            )
            .filter(Q(activation_date__isnull=True) | Q(activation_date__lt=Now()))
            .filter(Q(expiration_date__isnull=True) | Q(expiration_date__gt=Now()))
            .get()
        )

        if coupon and not coupon.reusable:
            coupon_redemption = B2BCouponRedemption.objects.filter(
                coupon=coupon, order__status__in=(B2BOrder.FULFILLED, B2BOrder.REFUNDED)
            )
            if coupon_redemption.exists():
                raise B2BCoupon.DoesNotExist
        return coupon


class B2BCoupon(TimestampedModel, AuditableModel):
    """
    A coupon for B2B purchases
    """

    name = models.TextField()
    coupon_code = models.CharField(max_length=50)
    discount_percent = models.DecimalField(
        decimal_places=5,
        max_digits=20,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="If no product is selected, the coupon is valid for any product",
    )
    reusable = models.BooleanField(
        default=False,
        help_text="When checked, the coupon can be redeemed multiple times",
    )
    enabled = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True
    )
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable before this time",
    )
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the coupons will not be redeemable after this time",
    )

    objects = B2BCouponManager()

    @classmethod
    def get_audit_class(cls):
        return B2BCouponAudit

    def to_dict(self):
        """Serialize anything which would contribute to an audit trail"""
        return serialize_model_object(self)

    def __str__(self):
        return f"B2BCoupon {self.coupon_code}"


class B2BCouponAudit(AuditModel):
    """Audit table for B2BCoupon"""

    coupon = models.ForeignKey(B2BCoupon, null=True, on_delete=models.PROTECT)

    @classmethod
    def get_related_field_name(cls):
        return "coupon"


class B2BOrder(OrderAbstract, AuditableModel):
    """
    An order containing information for the purchase of enrollment codes by businesses or other bulk purchasers.
    Orders which are fulfilled represent successful completion of a purchase and are the source of truth
    for this information.
    """

    num_seats = models.PositiveIntegerField()
    email = models.EmailField()
    product_version = models.ForeignKey(ProductVersion, on_delete=models.PROTECT)
    per_item_price = models.DecimalField(decimal_places=2, max_digits=20)
    total_price = models.DecimalField(decimal_places=2, max_digits=20)
    unique_id = models.UUIDField(default=uuid.uuid4)
    coupon_payment_version = models.ForeignKey(
        CouponPaymentVersion, null=True, blank=True, on_delete=models.PROTECT
    )
    coupon = models.ForeignKey(
        B2BCoupon, null=True, blank=True, on_delete=models.PROTECT
    )
    discount = models.DecimalField(
        decimal_places=2, max_digits=20, null=True, blank=True
    )
    contract_number = models.CharField(max_length=50, null=True, blank=True)
    program_run = models.ForeignKey(
        "courses.ProgramRun",
        blank=True,
        null=True,
        help_text="Program run to associate this order with",
        on_delete=models.PROTECT,
    )

    objects = OrderManager()

    @staticmethod
    def get_reference_number_prefix():
        """The reference number prefix used to match a CyberSource order fulfillment HTTP request with an order"""
        return f"{REFERENCE_NUMBER_PREFIX}{settings.ENVIRONMENT}"

    def __str__(self):
        """Description for CouponOrder"""
        return f"B2BOrder #{self.id}, status={self.status}"

    @classmethod
    def get_audit_class(cls):
        return B2BOrderAudit

    def to_dict(self):
        """
        Get a serialized representation of the B2BOrder
        """
        return {
            **serialize_model_object(self),
            "product_version_info": {
                **serialize_model_object(self.product_version),
                "product_info": {
                    **serialize_model_object(self.product_version.product),
                    "content_type_string": str(
                        self.product_version.product.content_type
                    ),
                    "content_object": serialize_model_object(
                        self.product_version.product.content_object
                    ),
                },
            },
            "receipts": [
                serialize_model_object(receipt) for receipt in self.b2breceipt_set.all()
            ],
        }

    @property
    def integration_id(self):
        """
        Return an integration id to be used by Hubspot as the unique deal id.
        This is necessary to prevent overlap with Order ids.

        Returns:
            str: the integration id
        """
        return f"{B2B_INTEGRATION_PREFIX}{self.id}"


class B2BOrderAudit(AuditModel):
    """
    Audit model for CouponOrder. This table is only meant for recordkeeping purposes. The serialized
    orders will also include information from any related tables.
    """

    order = models.ForeignKey(B2BOrder, null=True, on_delete=models.PROTECT)

    @classmethod
    def get_related_field_name(cls):
        return "order"


class B2BReceipt(TimestampedModel):
    """
    The contents of the message from CyberSource about an Order fulfillment or cancellation. The order
    should always exist but it's nullable in case there is a problem matching the CyberSource response to the order.
    """

    order = models.ForeignKey(B2BOrder, null=True, on_delete=models.PROTECT)
    data = JSONField()

    def __str__(self):
        """Description of B2BReceipt"""
        if self.order:
            return f"B2BReceipt for order {self.order.id}"
        else:
            return "B2BReceipt with no attached order"


class B2BCouponRedemption(TimestampedModel):
    """
    Link between a coupon and an order which used it.
    """

    coupon = models.ForeignKey(B2BCoupon, on_delete=models.PROTECT)
    order = models.ForeignKey(B2BOrder, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("coupon", "order")

    def __str__(self):
        return f"B2BCouponRedemption for {self.coupon} and {self.order}"
