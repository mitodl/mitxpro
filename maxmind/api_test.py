"""
Tests for the MaxMind IP lookup stuff.
"""

import ipaddress

import faker
import pytest

from maxmind.api import ip_to_country_code
from maxmind.factories import NetBlockIPv4Factory, NetBlockIPv6Factory

fake = faker.Factory.create()


@pytest.mark.django_db()
@pytest.mark.parametrize(
    "v4,in_block",  # noqa: PT006
    [
        [True, True],  # noqa: PT007
        [True, False],  # noqa: PT007
        [False, True],  # noqa: PT007
        [False, False],  # noqa: PT007
    ],
)
def test_ipv4_lookup(v4, in_block):
    """
    Test to see if a given IPv4 address can be looked up. If the IP is in a
    netblock we've seen, then you should get a country code back. If not, you
    should get None.
    """
    factory_block = NetBlockIPv4Factory.create() if v4 else NetBlockIPv6Factory.create()

    netblock = (
        ipaddress.IPv4Network(factory_block.network)
        if v4
        else ipaddress.IPv6Network(factory_block.network)
    )

    while True:
        test_address = ipaddress.ip_address(fake.ipv4() if v4 else fake.ipv6())
        if (
            in_block
            and (
                int(test_address) > int(netblock[0])
                and int(test_address) < int(netblock[-1])
            )
        ) or (
            int(test_address) < int(netblock[0])
            or int(test_address) > int(netblock[-1])
        ):
            break

    result = ip_to_country_code(str(test_address))

    assert (result is not None and in_block) or result is None
