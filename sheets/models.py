"""Sheets app models"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import DateTimeField, Model, PositiveSmallIntegerField

from mitxpro.models import SingletonModel, TimestampedModel
from sheets.constants import VALID_SHEET_TYPES


class GoogleApiAuth(TimestampedModel, SingletonModel):
    """Model that stores OAuth credentials to be used to authenticate with the Google API"""

    requesting_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    access_token = models.CharField(max_length=2048)
    refresh_token = models.CharField(null=True, max_length=512)  # noqa: DJ001


class CouponGenerationRequest(TimestampedModel):
    """Model that represents a request to create bulk enrollment coupons"""

    purchase_order_id = models.CharField(max_length=100, null=False)
    coupon_name = models.CharField(max_length=256, db_index=True, null=False)
    date_completed = models.DateTimeField(null=True, blank=True)
    raw_data = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001

    def __str__(self):
        return f"CouponGenerationRequest: id={self.id}, coupon_name={self.coupon_name}, purchase_order_id={self.purchase_order_id}, completed={self.date_completed is not None}"


class EnrollmentChangeRequestModel(TimestampedModel):
    """Model that represents a request to change an enrollment"""

    form_response_id = models.IntegerField(db_index=True, unique=True, null=False)
    date_completed = models.DateTimeField(null=True, blank=True)
    raw_data = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001

    class Meta:
        abstract = True


class RefundRequest(EnrollmentChangeRequestModel):
    """Model that represents a request to refund an enrollment"""

    def __str__(self):
        return f"RefundRequest: id={self.id}, form_response_id={self.form_response_id}, completed={self.date_completed is not None}"


class DeferralRequest(EnrollmentChangeRequestModel):
    """Model that represents a request to defer an enrollment"""

    def __str__(self):
        return f"DeferralRequest: id={self.id}, form_response_id={self.form_response_id}, completed={self.date_completed is not None}"


class GoogleFileWatch(TimestampedModel):
    """
    Model that represents a file watch/push notification/webhook that was set up via the Google API for
    some Google Drive file
    """

    file_id = models.CharField(max_length=100, db_index=True, null=False)
    channel_id = models.CharField(max_length=100, db_index=True, null=False)
    version = models.IntegerField(db_index=True, null=True, blank=True)
    activation_date = models.DateTimeField(null=False)
    expiration_date = models.DateTimeField(null=False)
    last_request_received = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("file_id", "version")

    def save(
        self,
        force_insert=False,  # noqa: FBT002
        force_update=False,  # noqa: FBT002
        using=None,
        update_fields=None,
    ):
        if (
            force_insert
            and self._meta.model.objects.filter(file_id=self.file_id).count() > 0
        ):
            raise ValidationError(
                f"Only one {self.__class__.__name__} object should exist for each unique file_id (file_id provided: {self.file_id}). "  # noqa: EM102
                "Update the existing object instead of creating a new one."
            )
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self):
        return f"GoogleFileWatch: id={self.id}, channel_id={self.channel_id}, file_id={self.file_id}, expires={self.expiration_date.isoformat()}"


class FileWatchRenewalAttempt(Model):  # noqa: DJ008
    """
    Tracks attempts to renew a Google file watch. Used for debugging flaky endpoint.
    """

    sheet_type = models.CharField(
        max_length=30,
        choices=zip(VALID_SHEET_TYPES, VALID_SHEET_TYPES),
        db_index=True,
        null=False,
    )
    sheet_file_id = models.CharField(max_length=100, db_index=True, null=False)
    date_attempted = DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=300, null=True, blank=True)  # noqa: DJ001
    result_status_code = PositiveSmallIntegerField(null=True, blank=True)
