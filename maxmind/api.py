"""MaxMind API functions"""

import csv
import ipaddress
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from maxmind import models

MAXMIND_CSV_COUNTRY_LOCATIONS_LITE = "geolite2-country-locations"
MAXMIND_CSV_COUNTRY_BLOCKS_IPV4_LITE = "geolite2-country-ipv4"
MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE = "geolite2-country-ipv6"
MAXMIND_CSV_TYPES = [
    MAXMIND_CSV_COUNTRY_LOCATIONS_LITE,
    MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE,
    MAXMIND_CSV_COUNTRY_BLOCKS_IPV4_LITE,
]


def import_maxmind_database(import_type: str, import_filename: str) -> None:
    """
    Imports the specified import file into the appropriate table. This only
    supports the GeoLite2 country location and network block files for now
    (these are all we care about at the moment).

    Args:
        - import_type (str): The import type, one of MAXMIND_CSV_TYPES
        - import_filename (str): The CSV format file to import.
    Returns:
        - None
    """

    if import_type not in MAXMIND_CSV_TYPES:
        raise Exception(f"Invalid database type {import_type}")  # noqa: EM102, TRY002

    rows = []

    with open(import_filename) as import_raw:  # noqa: PTH123
        dr = csv.DictReader(import_raw)

        for row in dr:
            if import_type == MAXMIND_CSV_COUNTRY_LOCATIONS_LITE:
                rows.append(
                    models.Geoname(
                        geoname_id=row["geoname_id"],
                        locale_code=row["locale_code"],
                        continent_code=row["continent_code"],
                        continent_name=row["continent_name"],
                        country_iso_code=row["country_iso_code"],
                        country_name=row["country_name"],
                        subdivision_1_iso_code=row["subdivision_1_iso_code"]  # noqa: SIM401
                        if "subdivision_1_iso_code" in row
                        else None,
                        subdivision_1_name=row["subdivision_1_name"]  # noqa: SIM401
                        if "subdivision_1_name" in row
                        else None,
                        subdivision_2_iso_code=row["subdivision_2_iso_code"]  # noqa: SIM401
                        if "subdivision_2_iso_code" in row
                        else None,
                        subdivision_2_name=row["subdivision_2_name"]  # noqa: SIM401
                        if "subdivision_2_name" in row
                        else None,
                        city_name=row["city_name"] if "city_name" in row else None,  # noqa: SIM401
                        metro_code=row["metro_code"] if "metro_code" in row else None,  # noqa: SIM401
                        time_zone=row["time_zone"] if "time_zone" in row else None,  # noqa: SIM401
                        is_in_european_union=row["is_in_european_union"]  # noqa: SIM401
                        if "is_in_european_union" in row
                        else None,
                    )
                )
            elif import_type in [
                MAXMIND_CSV_COUNTRY_BLOCKS_IPV4_LITE,
                MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE,
            ]:
                if len(row["geoname_id"]) == 0:
                    continue

                is_ipv6 = import_type == MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE
                netblock = (
                    ipaddress.IPv6Network(row["network"])
                    if is_ipv6
                    else ipaddress.IPv4Network(row["network"])
                )

                decimal_ip_start = Decimal(int(netblock[0]))
                ip_start = netblock[0]
                decimal_ip_end = Decimal(int(netblock[-1]))
                ip_end = netblock[-1]

                rows.append(
                    models.NetBlock(
                        is_ipv6=is_ipv6,
                        decimal_ip_start=decimal_ip_start,
                        decimal_ip_end=decimal_ip_end,
                        ip_start=ip_start,
                        ip_end=ip_end,
                        network=row["network"],
                        geoname_id=row["geoname_id"]
                        if "geoname_id" in row and len(row["geoname_id"]) > 0
                        else None,
                        registered_country_geoname_id=row[
                            "registered_country_geoname_id"
                        ]
                        if "registered_country_geoname_id" in row
                        and len(row["registered_country_geoname_id"]) > 0
                        else None,
                        represented_country_geoname_id=row[
                            "represented_country_geoname_id"
                        ]
                        if "represented_country_geoname_id" in row
                        and len(row["represented_country_geoname_id"]) > 0
                        else None,
                        is_anonymous_proxy=row["is_anonymous_proxy"]  # noqa: SIM401
                        if "is_anonymous_proxy" in row
                        else None,
                        is_satellite_provider=row["is_satellite_provider"]  # noqa: SIM401
                        if "is_satellite_provider" in row
                        else None,
                        postal_code=row["postal_code"]  # noqa: SIM401
                        if "postal_code" in row
                        else None,
                        latitude=row["latitude"] if "latitude" in row else None,  # noqa: SIM401
                        longitude=row["longitude"] if "longitude" in row else None,  # noqa: SIM401
                        accuracy_radius=row["accuracy_radius"]  # noqa: SIM401
                        if "accuracy_radius" in row
                        else None,
                    )
                )

    if len(rows) == 0:
        raise Exception("No rows to process - file format invalid?")  # noqa: EM101, TRY002

    with transaction.atomic():
        if import_type == MAXMIND_CSV_COUNTRY_LOCATIONS_LITE:
            models.Geoname.objects.all().delete()
            models.Geoname.objects.bulk_create(rows)
        elif import_type in (
            MAXMIND_CSV_COUNTRY_BLOCKS_IPV4_LITE,
            MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE,
        ):
            models.NetBlock.objects.filter(is_ipv6=False).delete()

        if import_type in [
            MAXMIND_CSV_COUNTRY_BLOCKS_IPV4_LITE,
            MAXMIND_CSV_COUNTRY_BLOCKS_IPV6_LITE,
        ]:
            models.NetBlock.objects.bulk_create(rows)


def ip_to_country_code(ip_address: str, locale: str = "en") -> str:
    """
    Uses the imported MaxMind databases to determine where the specified IP has
    been assigned.

    The country location data can be localized in a number of languages - if the
    locale is not specified, this defaults to English, so ensure you've imported
    the English data alongside any other language you require.

    Args:
        - ip_address (str): IP address as a string. This can be IPv4 or v6.
        - locale (str): The locale to use (default 'en').
    Returns:
        - None or ISO 3166 alpha2 code of the assigned country.
    """

    netaddr = ipaddress.ip_address(ip_address)

    ip_qset = models.NetBlock.objects.filter(
        decimal_ip_start__lte=int(netaddr), decimal_ip_end__gte=int(netaddr)
    )

    if not ip_qset.exists():
        return None

    netblock = ip_qset.get()
    location = (
        models.Geoname.objects.filter(locale_code=locale)
        .filter(
            Q(geoname_id=netblock.geoname_id)
            | Q(geoname_id=netblock.registered_country_geoname_id)
            | Q(geoname_id=netblock.represented_country_geoname_id)
        )
        .first()
    )

    return location.country_iso_code
