""" Factories for Hubspot """
from datetime import timezone

from factory import Faker
from factory.django import DjangoModelFactory

from hubspot.models import HubspotErrorCheck


class HubspotErrorCheckFactory(DjangoModelFactory):
    """Factory for HubspotErrorCheck"""

    checked_on = Faker(
        "date_time_this_year", before_now=True, after_now=False, tzinfo=timezone.utc
    )

    class Meta:
        model = HubspotErrorCheck
