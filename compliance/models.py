"""Compliance app models"""
from django.conf import settings
from django.db import models

from compliance.constants import (
    RESULT_CHOICES,
    RESULT_SUCCESS,
    RESULT_DENIED,
    RESULT_UNKNOWN,
    RESULT_MANUALLY_APPROVED,
)
from mitxpro.models import TimestampedModel


class ExportsInquiryLog(TimestampedModel):
    """
    Model to track exports exports_inquiries
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exports_inquiries",
    )

    computed_result = models.CharField(
        max_length=30, choices=zip(RESULT_CHOICES, RESULT_CHOICES)
    )

    reason_code = models.IntegerField()
    info_code = models.CharField(max_length=255, null=True)

    encrypted_request = models.TextField()
    encrypted_response = models.TextField()

    @property
    def is_denied(self):
        """Returns true if the export result was denied"""
        return self.computed_result == RESULT_DENIED

    @property
    def is_success(self):
        """Returns true if the export result was a success"""
        return self.computed_result in (RESULT_SUCCESS, RESULT_MANUALLY_APPROVED)

    @property
    def is_unknown(self):
        """Returns true if the export result was unknown"""
        return self.computed_result == RESULT_UNKNOWN
