"""Courseware models"""
from django.conf import settings
from django.db import models

from mitxpro.models import TimestampedModel
from courseware.constants import COURSEWARE_PLATFORM_CHOICES, PLATFORM_EDX


class CoursewareUser(TimestampedModel):
    """Model representing a User in a courseware platform"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(
        max_length=20, choices=COURSEWARE_PLATFORM_CHOICES, default=PLATFORM_EDX
    )
    has_been_synced = models.BooleanField(
        default=True,
        help_text="Indicates whether a corresponding user has been created on the courseware platform",
    )

    class Meta:
        unique_together = ("user", "platform")
