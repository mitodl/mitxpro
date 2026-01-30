"""
Factories for MaxMind data
"""

import ipaddress

import faker
from factory import LazyAttribute, LazyFunction, fuzzy
from factory.django import DjangoModelFactory

from maxmind import models

fake = faker.Faker()


class GeonameFactory(DjangoModelFactory):
    """Factory for Geoname"""

    geoname_id = fuzzy.FuzzyInteger(0, 2147483647)
    locale_code = "en"
    continent_code = fuzzy.FuzzyText(length=2)
    continent_name = fake.unique.last_name()
    country_iso_code = fake.unique.country_code()
    country_name = fake.unique.country()

    class Meta:
        model = models.Geoname


class NetBlockIPv4Factory(DjangoModelFactory):
    """Factory for NetBlock (IPv4 version)"""

    is_ipv6 = False

    network = fake.unique.ipv4(network=True)

    geoname_id = LazyFunction(lambda: GeonameFactory.create().geoname_id)

    decimal_ip_start = LazyAttribute(
        lambda obj: int(ipaddress.IPv4Network(obj.network)[0])
    )
    decimal_ip_end = LazyAttribute(
        lambda obj: int(ipaddress.IPv4Network(obj.network)[-1])
    )
    ip_start = LazyAttribute(lambda obj: ipaddress.IPv4Network(obj.network)[0])
    ip_end = LazyAttribute(lambda obj: ipaddress.IPv4Network(obj.network)[-1])

    class Meta:
        model = models.NetBlock


class NetBlockIPv6Factory(DjangoModelFactory):
    """Factory for NetBlock (IPv6 version)"""

    is_ipv6 = True

    network = fake.unique.ipv6(network=True)

    geoname_id = LazyFunction(lambda: GeonameFactory.create().geoname_id)

    decimal_ip_start = LazyAttribute(
        lambda obj: int(ipaddress.IPv6Network(obj.network)[0])
    )
    decimal_ip_end = LazyAttribute(
        lambda obj: int(ipaddress.IPv6Network(obj.network)[-1])
    )
    ip_start = LazyAttribute(lambda obj: ipaddress.IPv6Network(obj.network)[0])
    ip_end = LazyAttribute(lambda obj: ipaddress.IPv6Network(obj.network)[-1])

    class Meta:
        model = models.NetBlock
