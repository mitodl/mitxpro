"""mitxpro utilities"""
import datetime
from enum import auto, Flag
import json
import logging
import itertools
from urllib.parse import urlparse, urlunparse, ParseResult
import pytz

from django.conf import settings
from django.core.serializers import serialize
from django.db import models

log = logging.getLogger(__name__)


class FeatureFlag(Flag):
    """
    FeatureFlag enum

    Members should have values of increasing powers of 2 (1, 2, 4, 8, ...)

    """

    EXAMPLE_FEATURE = auto()


def webpack_dev_server_host(request):
    """
    Get the correct webpack dev server host
    """
    return settings.WEBPACK_DEV_SERVER_HOST or request.get_host().split(":")[0]


def webpack_dev_server_url(request):
    """
    Get the full URL where the webpack dev server should be running
    """
    return "http://{}:{}".format(
        webpack_dev_server_host(request), settings.WEBPACK_DEV_SERVER_PORT
    )


def is_near_now(time):
    """
    Returns true if time is within five seconds or so of now
    Args:
        time (datetime.datetime):
            The time to test
    Returns:
        bool:
            True if near now, false otherwise
    """
    now = datetime.datetime.now(tz=pytz.UTC)
    five_seconds = datetime.timedelta(0, 5)
    return now - five_seconds < time < now + five_seconds


def now_in_utc():
    """
    Get the current time in UTC
    Returns:
        datetime.datetime: A datetime object for the current time
    """
    return datetime.datetime.now(tz=pytz.UTC)


def dict_without_keys(d, *omitkeys):
    """
    Returns a copy of a dict without the specified keys

    Args:
        d (dict): A dict that to omit keys from
        *omitkeys: Variable length list of keys to omit

    Returns:
        dict: A dict with omitted keys
    """
    return {key: d[key] for key in d.keys() if key not in omitkeys}


def filter_dict_by_key_set(dict_to_filter, key_set):
    """Takes a dictionary and returns a copy with only the keys that exist in the given set"""
    return {key: dict_to_filter[key] for key in dict_to_filter.keys() if key in key_set}


def serialize_model_object(obj):
    """
    Serialize model into a dict representable as JSON
    Args:
        obj (django.db.models.Model): An instantiated Django model
    Returns:
        dict:
            A representation of the model
    """
    # serialize works on iterables so we need to wrap object in a list, then unwrap it
    data = json.loads(serialize("json", [obj]))[0]
    serialized = data["fields"]
    serialized["id"] = data["pk"]
    return serialized


def get_field_names(model):
    """
    Get field names which aren't autogenerated
    Args:
        model (class extending django.db.models.Model): A Django model class
    Returns:
        list of str:
            A list of field names
    """
    return [
        field.name
        for field in model._meta.get_fields()
        if not field.auto_created  # pylint: disable=protected-access
    ]


def first_matching_item(iterable, predicate):
    """
    Gets the first item in an iterable that matches a predicate (or None if nothing matches)

    Returns:
        Matching item or None
    """
    return next(filter(predicate, iterable), None)


def has_equal_properties(obj, property_dict):
    """
    Returns True if the given object has the properties indicated by the keys of the given dict, and the values
    of those properties match the values of the dict
    """
    for field, value in property_dict.items():
        try:
            if getattr(obj, field) != value:
                return False
        except AttributeError:
            return False
    return True


def first_or_none(iterable):
    """
    Returns the first item in an iterable, or None if the iterable is empty

    Args:
        iterable (iterable): Some iterable
    Returns:
        first item or None
    """
    return next((x for x in iterable), None)


def partition(items, predicate=bool):
    """
    Partitions an iterable into two different iterables - the first does not match the given condition, and the second
    does match the given condition.

    Args:
        items (iterable): An iterable of items to partition
        predicate (function): A function that takes each item and returns True or False
    Returns:
        tuple of iterables: An iterable of non-matching items, paired with an iterable of matching items
    """
    a, b = itertools.tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred), (item for pred, item in b if pred))


def unique(iterable):
    """
    Returns a generator containing all unique items in an iterable

    Args:
        iterable (iterable): An iterable of any hashable items
    Returns:
        generator: Unique items in the given iterable
    """
    seen = set()
    return (x for x in iterable if x not in seen and not seen.add(x))


def unique_ignore_case(strings):
    """
    Returns a generator containing all unique strings (coerced to lowercase) in a given iterable

    Args:
        strings (iterable of str): An iterable of strings
    Returns:
        generator: Unique lowercase strings in the given iterable
    """
    seen = set()
    return (s for s in map(str.lower, strings) if s not in seen and not seen.add(s))


class ValidateOnSaveMixin(models.Model):
    """Mixin that calls field/model validation methods before saving a model object"""

    class Meta:
        abstract = True

    def save(
        self, force_insert=False, force_update=False, **kwargs
    ):  # pylint: disable=arguments-differ
        if not (force_insert or force_update):
            self.full_clean()
        super().save(force_insert=force_insert, force_update=force_update, **kwargs)


def remove_password_from_url(url):
    """
    Remove a password from a URL

    Args:
        url (str): A URL

    Returns:
        str: A URL without a password
    """
    pieces = urlparse(url)
    netloc = pieces.netloc
    userinfo, delimiter, hostinfo = netloc.rpartition("@")
    if delimiter:
        username, _, _ = userinfo.partition(":")
        rejoined_netloc = f"{username}{delimiter}{hostinfo}"
    else:
        rejoined_netloc = netloc

    return urlunparse(
        ParseResult(
            scheme=pieces.scheme,
            netloc=rejoined_netloc,
            path=pieces.path,
            params=pieces.params,
            query=pieces.query,
            fragment=pieces.fragment,
        )
    )
