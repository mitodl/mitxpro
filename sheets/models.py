from django.conf import settings
from django.db import models

from mitxpro.models import TimestampedModel


class GoogleToken(models.Model):
    value = models.BinaryField()


class GoogleApiAuth(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        unique=True,
    )
    access_token = models.CharField(max_length=2048)
    refresh_token = models.CharField(null=True, max_length=512)
    id_token = models.CharField(null=True, max_length=256)


class CouponGenerationRequest(TimestampedModel):
    transaction_id = models.CharField(max_length=100, db_index=True, null=False)
    completed = models.BooleanField(default=False)
    spreadsheet_updated = models.BooleanField(default=False)
