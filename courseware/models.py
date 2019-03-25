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


class OpenEdxApiAuth(TimestampedModel):
    """Model that stores OAuth2 tokens for authenticating Open edX API calls"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    refresh_token = models.CharField(max_length=128)
    access_token = models.CharField(null=True, max_length=128)
    access_token_expires_on = models.DateTimeField(null=True)

    class Meta:
        index_together = ("user", "access_token_expires_on")
