"""Model definitions for affiliate tracking"""
from django.conf import settings
from django.db import models

from mitxpro.models import TimestampedModel


class Affiliate(TimestampedModel):
    """Model that represents an affiliate"""

    code = models.CharField(max_length=20, db_index=True, unique=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return "Affiliate: id={}, code={}, name={}".format(
            self.id, self.code, self.name
        )


class AffiliateReferralAction(TimestampedModel):
    """Model that represents some action that was taken by a user"""

    affiliate = models.ForeignKey(
        Affiliate, on_delete=models.CASCADE, related_name="affiliate_referral_actions"
    )
    created_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="affiliate_user_actions",
        null=True,
        blank=True,
    )
    created_order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.CASCADE,
        related_name="affiliate_order_actions",
        null=True,
        blank=True,
    )

    def __str__(self):
        return "AffiliateReferralAction: code={}, created_user_id={}, created_order_id={}".format(
            self.affiliate.code, self.created_user_id, self.created_order_id
        )
