from django.db import models

from mitxpro.models import TimestampedModel


class GoogleToken(models.Model):
    value = models.BinaryField()


class ServiceAccountCredentials(TimestampedModel):
    value = models.TextField(max_length=3000, null=False)


class CouponGenerationRequest(TimestampedModel):
    transaction_id = models.CharField(max_length=100, db_index=True, null=False)
    completed = models.BooleanField(default=False)
    spreadsheet_updated = models.BooleanField(default=False)
