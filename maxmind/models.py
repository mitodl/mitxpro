"""MaxMind models"""

from django.db import models


class Geoname(models.Model):
    """
    Stores the locations - the mappings between the geoname stored in
    the IP block databases and the location where they reside. This works for
    both the City data and the Country data.

    MaxMind distributes this in several languages; import whichever is required
    for your use case. Multiple languages can be imported as well.

    This model implements the spec found here:
    https://dev.maxmind.com/geoip/docs/databases/city-and-country/#locations-files
    """

    geoname_id = models.IntegerField()
    locale_code = models.TextField()
    continent_code = models.CharField(max_length=2)
    continent_name = models.TextField()
    country_iso_code = models.CharField(max_length=2)
    country_name = models.TextField()
    subdivision_1_iso_code = models.CharField(max_length=3, blank=True, null=True)
    subdivision_1_name = models.TextField(blank=True, null=True)
    subdivision_2_iso_code = models.CharField(max_length=3, blank=True, null=True)
    subdivision_2_name = models.TextField(blank=True, null=True)
    city_name = models.TextField(blank=True, null=True)
    metro_code = models.IntegerField(blank=True, null=True)
    time_zone = models.TextField(blank=True, null=True)
    is_in_european_union = models.BooleanField(blank=True, null=True, default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["geoname_id", "locale_code"], name="unique_geoname_id_locale"
            )
        ]

    def __str__(self):
        return f"{self.geoname_id} {self.locale_code}: {self.subdivision_2_iso_code} {self.subdivision_1_iso_code} {self.country_iso_code} {self.continent_code}"


class NetBlock(models.Model):
    """
    Stores the network blocks. The same table stores both IPv4 and IPv6 blocks.
    The geoname_id field plus the locale code can be used to look up the
    location for a given IP.

    This also stores block range converted to beginning and ending IPs in
    decimal format, to assist in determining what netblock a given IP belongs
    to. Note that both IPv4 and IPv6 addresses can be expressed in base 10, so
    there will be some overlap for these addresses. Make sure your search
    includes "is_ipv6" to make sure you don't get (say) IPv6 netblocks back when
    looking for an IPv4 address.

    The spec for the MaxMind part of this table is here:
    https://dev.maxmind.com/geoip/docs/databases/city-and-country/#blocks-files
    """

    is_ipv6 = models.BooleanField(default=False, blank=True)
    # IPv6 addresses are 128 bits long, so they don't necessarily fit in a
    # PositiveBigInteger/BigInteger (which have the same positive max values)
    decimal_ip_start = models.DecimalField(
        max_digits=39, decimal_places=0, blank=True, null=True
    )
    decimal_ip_end = models.DecimalField(
        max_digits=39, decimal_places=0, blank=True, null=True
    )
    ip_start = models.TextField(blank=True)
    ip_end = models.TextField(blank=True)

    network = models.TextField()
    # These three GeoName ID fields can all be null - one must be specified
    # but any of the others can be blank
    geoname_id = models.BigIntegerField(blank=True, null=True)
    registered_country_geoname_id = models.BigIntegerField(blank=True, null=True)
    represented_country_geoname_id = models.BigIntegerField(blank=True, null=True)
    is_anonymous_proxy = models.BooleanField(default=False, null=True, blank=True)
    is_satellite_provider = models.BooleanField(default=False, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=16, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=16, decimal_places=6, blank=True, null=True
    )
    accuracy_radius = models.IntegerField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(geoname_id__isnull=False)
                | models.Q(registered_country_geoname_id__isnull=False)
                | models.Q(represented_country_geoname_id__isnull=False),
                name="at_least_one_geoname_id",
            )
        ]
        indexes = [
            models.Index(fields=["decimal_ip_start"]),
            models.Index(fields=["decimal_ip_end"]),
            models.Index(fields=["decimal_ip_start", "decimal_ip_end"]),
        ]

    def __str__(self):
        return f"{self.geoname_id}: {self.network} (IPv6 {self.is_ipv6}) start {self.ip_start} end {self.ip_end}"
