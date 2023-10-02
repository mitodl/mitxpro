# MaxMind IP Location Lookup

This app provides a lookup for a client's country based on IP address, using the
MaxMind GeoLite2 databases (though it should also work with the more
fully-featured versions of th dataset as well). The APIs here allow for lookup
of both IPv4 and IPv6 addresses.

## Structure

There are three parts: models, API, and a management command.

### Models

The app stores the MaxMind data in its own tables for these reasons:

- Eliminating extra API calls: MaxMind does provide a Web service for this but that involves making an external API call (and thus additional processing time, etc.)
- More efficient storage of data: MaxMind also provides a Python client that can read their binary database files - but those are at least 8MB in size and require hitting the filesystem
- Ease of lookup: Since we just store the data in Postgres, it's available for adhoc queries, and can be optimized with custom indexing if so requierd

The model consists of two tables:

- `Geoname`: stores the locations that a given netblock is assigned to, potentially in a variety of locales/languages.
  - The available location data is dependent on the import file used. MaxMind provides several options here with varying subsets of data - for example, if you just need country code lookups, you can just import country data.
  - MaxMind provides location data in several localizations, all of which can be loaded simultaneously. The code _expects_ the English locale version to be there.
  - Because the data is localized, there is a unique constraint on the geoname ID and locale code fields. Also, notably, the `NetBlock` table does _not_ have a foreign key relationship because the key is a composite key.
- `NetBlock`: stores the known netblocks, both IPv4 and v6, and maps them to a Geoname entry.
  - The model supports IPv4 and IPv6, denoted by the `is_ipv6` flag.
  - While you do not need to load both sets of netblocks, it is recommended as some users may access your service via IPv6 only. If your service is not configured for IPv6, you can get away with just loading the IPv4 netblock data.

There is some transformation of the base MaxMind data that is done before it is
stored locally. Specifically, the import functionality calculates and stores the
first and last IP address in each netblock, in both IP address format (dotted
quad or IPv6) and in decimal format.

### API

`ip_to_country_code(ip_address: str, locale_code: str = 'en')`

Determines the netblock the IP address supplied belongs to, then returns the
ISO 3166-1 alpha2 code that the block is assigned to.

The `locale_code` field defaults to `en`; if you have data imported for other
locales, you can specify that. Note that this function returns a standardized
country code, though, and those aren't localized.

### Management Command

`import_maxmind_data <data file> <type>`

Imports the MaxMind database specified. The data file should be in CSV format,
and the type should be one of the types specified in `api.py` (in
`MAXMIND_CSV_TYPES`).

The GeoLite2 database is available free of charge after registering for a
MaxMind account here: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data

The regular GeoIP2 databases should also be compatible, and the data should be
retained for those, but the API only returns country codes currently.
