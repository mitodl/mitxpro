"""Utils tests"""
import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytz

from ecommerce.models import Order
from mitxpro.utils import (
    format_price,
    get_field_names,
    now_in_utc,
    is_near_now,
    dict_without_keys,
    filter_dict_by_key_set,
    make_csv_http_response,
    partition,
    has_equal_properties,
    remove_password_from_url,
    first_or_none,
    find_object_with_matching_attr,
    unique,
    unique_ignore_case,
    max_or_none,
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


def test_has_equal_properties():
    """
    Assert that has_equal_properties returns True if an object has equivalent properties to a given dict
    """
    obj = SimpleNamespace(a=1, b=2, c=3)
    assert has_equal_properties(obj, {}) is True
    assert has_equal_properties(obj, dict(a=1, b=2)) is True
    assert has_equal_properties(obj, dict(a=1, b=2, c=3)) is True
    assert has_equal_properties(obj, dict(a=2)) is False
    assert has_equal_properties(obj, dict(d=4)) is False


def test_find_object_with_matching_attr():
    """
    Assert that find_object_with_matching_attr returns the first object in an iterable that has the given
    attribute value (or None if there is no match)
    """
    objects = [
        SimpleNamespace(a=0),
        SimpleNamespace(a=1),
        SimpleNamespace(a=2),
        SimpleNamespace(a=3),
        SimpleNamespace(a=None),
    ]
    assert find_object_with_matching_attr(objects, "a", 3) == objects[3]
    assert find_object_with_matching_attr(objects, "a", None) == objects[4]
    assert find_object_with_matching_attr(objects, "a", "bad value") is None
    assert find_object_with_matching_attr(objects, "b", None) is None


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


@pytest.mark.parametrize(
    "url, expected",
    [
        ["", ""],
        ["http://url.com/url/here#other", "http://url.com/url/here#other"],
        ["https://user:pass@sentry.io/12345", "https://user@sentry.io/12345"],
    ],
)
def test_remove_password_from_url(url, expected):
    """Assert that the url is parsed and the password is not present in the returned value, if provided"""
    assert remove_password_from_url(url) == expected


def test_first_or_none():
    """
    Assert that first_or_none returns the first item in an iterable or None
    """
    assert first_or_none([]) is None
    assert first_or_none(set()) is None
    assert first_or_none([1, 2, 3]) == 1
    assert first_or_none(range(1, 5)) == 1


def test_max_or_none():
    """
    Assert that max_or_none returns the max of some iterable, or None if the iterable has no items
    """
    assert max_or_none(i for i in [5, 4, 3, 2, 1]) == 5
    assert max_or_none([1, 3, 5, 4, 2]) == 5
    assert max_or_none([]) is None


def test_unique():
    """
    Assert that unique() returns a generator of unique elements from a provided iterable
    """
    assert list(unique([1, 2, 2, 3, 3, 0, 3])) == [1, 2, 3, 0]
    assert list(unique(("a", "b", "a", "c", "C", None))) == ["a", "b", "c", "C", None]


def test_unique_ignore_case():
    """
    Assert that unique_ignore_case() returns a generator of unique lowercase strings from a
    provided iterable
    """
    assert list(unique_ignore_case(["ABC", "def", "AbC", "DEf"])) == ["abc", "def"]


@pytest.mark.parametrize(
    "price,expected",
    [[Decimal("0"), "$0.00"], [Decimal("1234567.89"), "$1,234,567.89"]],
)
def test_format_price(price, expected):
    """Format a decimal value into a price"""
    assert format_price(price) == expected


def test_make_csv_http_response():
    """
    make_csv_http_response should make a HttpResponse object suitable for serving a CSV file.
    """
    rows = [{"a": "B", "c": "d"}, {"a": "e", "c": "f"}]
    response = make_csv_http_response(csv_rows=rows, filename="test_filename")
    out_rows = [line.split(",") for line in response.content.decode().splitlines()]
    assert out_rows == [["a", "c"], ["B", "d"], ["e", "f"]]
    assert response["Content-Disposition"] == 'attachment; filename="test_filename"'
    assert response["Content-Type"] == "text/csv"


def test_make_csv_http_response_empty():
    """
    make_csv_http_response should handle empty data sets by returning an empty response
    """
    response = make_csv_http_response(csv_rows=[], filename="empty_filename")
    out_rows = [line.split(",") for line in response.content.decode().splitlines()]
    assert out_rows == []
    assert response["Content-Disposition"] == 'attachment; filename="empty_filename"'
    assert response["Content-Type"] == "text/csv"
