""" Hubspot models """
from django.db import models


class HubspotErrorCheck(models.Model):
    """
    Store the datetime of the most recent Hubspot API error check.
    """

    checked_on = models.DateTimeField()
