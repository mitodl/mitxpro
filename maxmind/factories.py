"""
Factories for MaxMind data
"""
import ipaddress

import faker
from factory import LazyFunction, PostGeneration, SubFactory, fuzzy
from factory.django import DjangoModelFactory

from maxmind import models


fake = faker.Factory.create()


class GeonameFactory(DjangoModelFactory):
    geoname_id = fuzzy.FuzzyInteger(0, 2147483647)
    locale_code = "en"
    continent_code = fuzzy.FuzzyText(length=2)
    continent_name = fake.last_name()
    country_iso_code = fake.country_code()
    country_name = fake.country()

    class Meta:
        model = models.Geoname


class NetBlockIPv4Factory(DjangoModelFactory):
    is_ipv6 = False

    network = fake.ipv4(network=True)

    geoname_id = LazyFunction(lambda: GeonameFactory.create().id)

    decimal_ip_start = PostGeneration(
        lambda obj, create, extracted, **kwargs: int(
            ipaddress.IPv4Network(obj.network)[0]
        )
    )
    decimal_ip_end = PostGeneration(
        lambda obj, create, extracted, **kwargs: int(
            ipaddress.IPv4Network(obj.network)[-1]
        )
    )
    ip_start = PostGeneration(
        lambda obj, create, extracted, **kwargs: ipaddress.IPv4Network(obj.network)[0]
    )
    ip_end = PostGeneration(
        lambda obj, create, extracted, **kwargs: ipaddress.IPv4Network(obj.network)[-1]
    )

    class Meta:
        model = models.NetBlock


class NetBlockIPv6Factory(DjangoModelFactory):
    is_ipv6 = True

    network = fake.ipv6(network=True)

    geoname_id = LazyFunction(lambda: GeonameFactory.create().id)

    decimal_ip_start = PostGeneration(
        lambda obj, create, extracted, **kwargs: int(
            ipaddress.IPv6Network(obj.network)[0]
        )
    )
    decimal_ip_end = PostGeneration(
        lambda obj, create, extracted, **kwargs: int(
            ipaddress.IPv6Network(obj.network)[-1]
        )
    )
    ip_start = PostGeneration(
        lambda obj, create, extracted, **kwargs: ipaddress.IPv6Network(obj.network)[0]
    )
    ip_end = PostGeneration(
        lambda obj, create, extracted, **kwargs: ipaddress.IPv6Network(obj.network)[-1]
    )

    class Meta:
        model = models.NetBlock
