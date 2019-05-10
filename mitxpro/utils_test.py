"""Utils tests"""
import datetime

import pytz

from ecommerce.models import Order
from mitxpro.utils import (
    get_field_names,
    now_in_utc,
    is_near_now,
    dict_without_keys,
    filter_dict_by_key_set,
    partition,
)


def test_now_in_utc():
    """now_in_utc() should return the current time set to the UTC time zone"""
    now = now_in_utc()
    assert is_near_now(now)
    assert now.tzinfo == pytz.UTC


def test_is_near_now():
    """
    Test is_near_now for now
    """
    now = datetime.datetime.now(tz=pytz.UTC)
    assert is_near_now(now) is True
    later = now + datetime.timedelta(0, 6)
    assert is_near_now(later) is False
    earlier = now - datetime.timedelta(0, 6)
    assert is_near_now(earlier) is False


def test_dict_without_keys():
    """
    Test that dict_without_keys returns a dict with keys omitted
    """
    d = {"a": 1, "b": 2, "c": 3}
    assert dict_without_keys(d, "a") == {"b": 2, "c": 3}
    assert dict_without_keys(d, "a", "b") == {"c": 3}
    assert dict_without_keys(d, "doesnt_exist") == d


def test_filter_dict_by_key_set():
    """
    Test that filter_dict_by_key_set returns a dict with only the given keys
    """
    d = {"a": 1, "b": 2, "c": 3, "d": 4}
    assert filter_dict_by_key_set(d, {"a", "c"}) == {"a": 1, "c": 3}
    assert filter_dict_by_key_set(d, {"a", "c", "nonsense"}) == {"a": 1, "c": 3}
    assert filter_dict_by_key_set(d, {"nonsense"}) == {}


def test_get_field_names():
    """
    Assert that get_field_names does not include related fields
    """
    assert set(get_field_names(Order)) == {
        "purchaser",
        "status",
        "created_on",
        "updated_on",
    }


def test_partition():
    """
    Assert that partition splits an iterable into two iterables according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition(nums, lambda n: n == 1)
    assert list(not_ones) == [2, 3, 4, 0, None, None]
    assert list(ones) == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition(nums)
    assert list(falsey) == [0, None, None]
    assert list(truthy) == [1, 2, 1, 3, 1, 4]
