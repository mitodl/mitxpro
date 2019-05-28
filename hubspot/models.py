""" Hubspot models """
from django.db import models


class HubspotErrorTimestamp(models.Model):
    """
    Store the timestamp of the most recent Hubspot API error.
    """

    checked_on = models.DateTimeField()
