"""Sheets app models"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from mitxpro.models import TimestampedModel


class GoogleApiAuth(TimestampedModel):
    """Model that stores OAuth credentials to be used to authenticate with the Google API"""

    requesting_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    access_token = models.CharField(max_length=2048)
    refresh_token = models.CharField(null=True, max_length=512)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # GoogleApiAuth should be a singleton, i.e.: there should never be more than one
        if force_insert and self._meta.model.objects.count() > 0:
            raise ValidationError(
                "Only one {} object should exist. Update the existing object instead "
                "of creating a new one.".format(self.__class__.__name__)
            )
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class CouponGenerationRequest(TimestampedModel):
    """Model that represents a request to create bulk enrollment coupons"""

    transaction_id = models.CharField(max_length=100, db_index=True, null=False)
    completed = models.BooleanField(default=False)
