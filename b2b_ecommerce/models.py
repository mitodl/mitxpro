"""Models for business to business ecommerce"""
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models

from b2b_ecommerce.constants import REFERENCE_NUMBER_PREFIX
from ecommerce.models import (
    CouponPaymentVersion,
    ProductVersion,
    OrderAbstract,
    OrderManager,
)
from mitxpro.models import AuditModel, AuditableModel, TimestampedModel
from mitxpro.utils import serialize_model_object


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
        CouponPaymentVersion, null=True, on_delete=models.PROTECT
    )

    reference_number_prefix = REFERENCE_NUMBER_PREFIX
    objects = OrderManager()

    @property
    def reference_id(self):
        """Create a string with the order id and a unique prefix so we can lookup the order during order fulfillment"""
        return f"{REFERENCE_NUMBER_PREFIX}{settings.CYBERSOURCE_REFERENCE_PREFIX}-{self.id}"

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
