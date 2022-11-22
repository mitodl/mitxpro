""" Hubspot models """
from django.db import models

from ecommerce.models import Line


class HubspotErrorCheck(models.Model):
    """
    Store the datetime of the most recent Hubspot API error check.
    """

    checked_on = models.DateTimeField()


class HubspotLineResync(models.Model):
    """
    Indicates that hubspot tried to sync a line before it's order and needs to be resynced
    """

    line = models.ForeignKey(Line, on_delete=models.CASCADE)
