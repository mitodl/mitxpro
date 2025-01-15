"""Utils tests"""

import datetime
import operator as op
import os
from decimal import Decimal
from types import SimpleNamespace

import pytest
from rest_framework import status

from ecommerce.api import is_tax_applicable
from ecommerce.models import Order
from mitxpro.test_utils import MockResponse
from mitxpro.utils import (
    all_equal,
    all_unique,
    clean_url,
    dict_without_keys,
    ensure_trailing_slash,
    filter_dict_by_key_set,
    find_object_with_matching_attr,
    first_matching_item,
    first_or_none,
    format_datetime_for_filename,
    format_price,
    get_error_response_summary,
    get_field_names,
    get_js_settings,
    group_into_dict,
    has_all_keys,
    has_equal_properties,
    is_json_response,
    is_near_now,
    item_at_index_or_blank,
    item_at_index_or_none,
    make_csv_http_response,
    matching_item_index,
    max_or_none,
    now_in_utc,
    partition,
    partition_to_lists,
    public_path,
    remove_password_from_url,
    request_get_with_timeout_retry,
    strip_datetime,
    unique,
    unique_ignore_case,
    webpack_dev_server_host,
    webpack_dev_server_url,
)


def test_ensure_trailing_slash():
    """Verify ensure_trailing_slash() enforces a single slash on the end"""
    assert ensure_trailing_slash("http://example.com") == "http://example.com/"
    assert ensure_trailing_slash("http://example.com/") == "http://example.com/"


def test_public_path(rf, settings):
    """Test public_path() behaviors"""
    request = rf.get("/")

    settings.WEBPACK_USE_DEV_SERVER = True
    assert public_path(request) == webpack_dev_server_url(request) + "/"

    settings.WEBPACK_USE_DEV_SERVER = False
    assert public_path(request) == "/static/bundles/"


def test_webpack_dev_server_host(settings, rf):
    """Test webpack_dev_server_host()"""
    request = rf.get("/", SERVER_NAME="invalid-dev-server1.local")
    settings.WEBPACK_DEV_SERVER_HOST = "invalid-dev-server2.local"
    assert webpack_dev_server_host(request) == "invalid-dev-server2.local"
    settings.WEBPACK_DEV_SERVER_HOST = None
    assert webpack_dev_server_host(request) == "invalid-dev-server1.local"


def test_webpack_dev_server_url(settings, rf):
    """Test webpack_dev_server_url()"""
    settings.WEBPACK_DEV_SERVER_PORT = 7777
    settings.WEBPACK_DEV_SERVER_HOST = "invalid-dev-server.local"
    request = rf.get("/")
    assert webpack_dev_server_url(request) == "http://invalid-dev-server.local:7777"


def test_now_in_utc():
    """now_in_utc() should return the current time set to the UTC time zone"""
    now = now_in_utc()
    assert is_near_now(now)
    assert now.tzinfo == datetime.UTC


def test_is_near_now():
    """
    Test is_near_now for now
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    assert is_near_now(now) is True
    later = now + datetime.timedelta(0, 6)
    assert is_near_now(later) is False
    earlier = now - datetime.timedelta(0, 6)
    assert is_near_now(earlier) is False


def test_format_datetime_for_filename():
    """
    Test that format_datetime_for_filename formats a datetime object to a string for use in a filename
    """
    dt = datetime.datetime(  # noqa: DTZ001
        year=2019, month=1, day=1, hour=20, minute=21, second=22, microsecond=100
    )
    assert format_datetime_for_filename(dt) == "20190101"
    assert format_datetime_for_filename(dt, include_time=True) == "20190101_202122"
    assert (
        format_datetime_for_filename(dt, include_time=True, include_ms=True)
        == "20190101_202122_000100"
    )
    assert format_datetime_for_filename(dt, include_ms=True) == "20190101_202122_000100"


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
        "total_price_paid",
        "tax_rate",
        "tax_rate_name",
        "tax_country_code",
    }


def test_has_equal_properties():
    """
    Assert that has_equal_properties returns True if an object has equivalent properties to a given dict
    """
    obj = SimpleNamespace(a=1, b=2, c=3)
    assert has_equal_properties(obj, {}) is True
    assert has_equal_properties(obj, dict(a=1, b=2)) is True  # noqa: C408
    assert has_equal_properties(obj, dict(a=1, b=2, c=3)) is True  # noqa: C408
    assert has_equal_properties(obj, dict(a=2)) is False  # noqa: C408
    assert has_equal_properties(obj, dict(d=4)) is False  # noqa: C408


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


def test_partition_to_lists():
    """
    Assert that partition_to_lists splits an iterable into two lists according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition_to_lists(nums, lambda n: n == 1)
    assert not_ones == [2, 3, 4, 0, None, None]
    assert ones == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition_to_lists(nums)
    assert falsey == [0, None, None]
    assert truthy == [1, 2, 1, 3, 1, 4]


@pytest.mark.parametrize(
    "url, expected",  # noqa: PT006
    [
        ["", ""],  # noqa: PT007
        ["http://url.com/url/here#other", "http://url.com/url/here#other"],  # noqa: PT007
        ["https://user:pass@sentry.io/12345", "https://user@sentry.io/12345"],  # noqa: PT007
    ],
)
def test_remove_password_from_url(url, expected):
    """Assert that the url is parsed and the password is not present in the returned value, if provided"""
    assert remove_password_from_url(url) == expected


def test_first_matching_item():
    """first_matching_item should return an item that matches a predicate, or None"""
    assert first_matching_item(["a", "b", "c", "b"], lambda x: x == "b") == "b"
    number_iter = (i for i in [2, 4, 6, 8, 9, 10])
    assert first_matching_item(number_iter, lambda i: i % 2 == 1) == 9
    assert first_matching_item([1, 2, 3, 4, 5], lambda i: i == 6) is None


def test_matching_item_index():
    """matching_item_index should return the index of an item equal to the given value, or raises an exception"""
    assert matching_item_index(["a", "b", "c", "d"], "b") == 1
    with pytest.raises(StopIteration):
        matching_item_index(["a", "b", "c", "d"], "e")
    number_iter = (i for i in [0, 1, 2, 3, 4])
    assert matching_item_index(number_iter, 2) == 2


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


def test_item_at_index_or_none():
    """
    Assert that item_at_index_or_none returns an item at a given index, or None if that index
    doesn't exist
    """
    arr = [1, 2, 3]
    assert item_at_index_or_none(arr, 1) == 2
    assert item_at_index_or_none(arr, 10) is None


def test_item_at_index_or_blank():
    """
    Assert that item_at_index_or_blank returns an item at a given index, or a blank string if that index
    doesn't exist
    """
    arr = ["string 1", "string 2"]
    assert item_at_index_or_blank(arr, 0) == "string 1"
    assert item_at_index_or_blank(arr, 1) == "string 2"
    assert item_at_index_or_blank(arr, 10) == ""


def test_all_equal():
    """
    Assert that all_equal returns True if all of the provided args are equal to each other
    """
    assert all_equal(1, 1, 1) is True
    assert all_equal(1, 2, 1) is False
    assert all_equal() is True


def test_all_unique():
    """
    Assert that all_unique returns True if all of the items in the iterable argument are unique
    """
    assert all_unique([1, 2, 3, 4]) is True
    assert all_unique((1, 2, 3, 4)) is True
    assert all_unique([1, 2, 3, 1]) is False


def test_has_all_keys():
    """
    Assert that has_all_keys returns True if the given dict has all of the specified keys
    """
    d = {"a": 1, "b": 2, "c": 3}
    assert has_all_keys(d, ["a", "c"]) is True
    assert has_all_keys(d, ["a", "z"]) is False


def test_group_into_dict():
    """
    Assert that group_into_dict takes an iterable of items and returns a dictionary of those items
    grouped by generated keys
    """

    class Car:
        def __init__(self, make, model):
            self.make = make
            self.model = model

    cars = [
        Car(make="Honda", model="Civic"),
        Car(make="Honda", model="Accord"),
        Car(make="Ford", model="F150"),
        Car(make="Ford", model="Focus"),
        Car(make="Jeep", model="Wrangler"),
    ]
    grouped_cars = group_into_dict(cars, key_fn=op.attrgetter("make"))
    assert set(grouped_cars.keys()) == {"Honda", "Ford", "Jeep"}
    assert set(grouped_cars["Honda"]) == set(cars[0:2])
    assert set(grouped_cars["Ford"]) == set(cars[2:4])
    assert grouped_cars["Jeep"] == [cars[4]]

    nums = [1, 2, 3, 4, 5, 6]
    grouped_nums = group_into_dict(nums, key_fn=lambda num: (num % 2 == 0))
    assert grouped_nums.keys() == {True, False}
    assert set(grouped_nums[True]) == {2, 4, 6}
    assert set(grouped_nums[False]) == {1, 3, 5}


@pytest.mark.parametrize(
    "price,expected",  # noqa: PT006
    [[Decimal("0"), "$0.00"], [Decimal("1234567.89"), "$1,234,567.89"]],  # noqa: PT007
)
def test_format_price(price, expected):
    """Format a decimal value into a price"""
    assert format_price(price) == expected


@pytest.mark.parametrize(
    "content,content_type,exp_summary_content,exp_url_in_summary",  # noqa: PT006
    [
        ['{"bad": "response"}', "application/json", '{"bad": "response"}', False],  # noqa: PT007
        ["plain text", "text/plain", "plain text", False],  # noqa: PT007
        [  # noqa: PT007
            "<div>HTML content</div>",
            "text/html; charset=utf-8",
            "(HTML body ignored)",
            True,
        ],
    ],
)
def test_get_error_response_summary(
    content, content_type, exp_summary_content, exp_url_in_summary
):
    """
    get_error_response_summary should provide a summary of an error HTTP response object with the correct bits of
    information depending on the type of content.
    """
    status_code = 400
    url = "http://example.com"
    mock_response = MockResponse(
        status_code=status_code, content=content, content_type=content_type, url=url
    )
    summary = get_error_response_summary(mock_response)
    assert f"Response - code: {status_code}" in summary
    assert f"content: {exp_summary_content}" in summary
    assert (f"url: {url}" in summary) is exp_url_in_summary


@pytest.mark.parametrize(
    "content,content_type,expected",  # noqa: PT006
    [
        ['{"bad": "response"}', "application/json", True],  # noqa: PT007
        ["plain text", "text/plain", False],  # noqa: PT007
        ["<div>HTML content</div>", "text/html; charset=utf-8", False],  # noqa: PT007
    ],
)
def test_is_json_response(content, content_type, expected):
    """
    is_json_response should return True if the given response's content type indicates JSON content
    """
    mock_response = MockResponse(
        status_code=400, content=content, content_type=content_type
    )
    assert is_json_response(mock_response) is expected


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


def test_request_get_with_timeout_retry(mocker):
    """request_get_with_timeout_retry should make a GET request and retry if the response status is 504 (timeout)"""
    mock_response = mocker.Mock(status_code=status.HTTP_504_GATEWAY_TIMEOUT)
    patched_request_get = mocker.patch(
        "mitxpro.utils.requests.get", return_value=mock_response
    )
    patched_log = mocker.patch("mitxpro.utils.log")
    url = "http://example.com/retry"
    retries = 4

    result = request_get_with_timeout_retry(url, retries=retries)
    assert patched_request_get.call_count == retries
    assert patched_log.warning.call_count == (retries - 1)
    mock_response.raise_for_status.assert_called_once()
    assert result == mock_response


def test_get_js_settings(settings, rf, user, mocker):
    """Test get_js_settings"""

    def posthog_is_enabled_side_effect(*args, **kwargs):
        """
        Side effect to return True/False for specific features while mocking posthog is_enabled.
        """
        return False

    settings.GA_TRACKING_ID = "fake"
    settings.GTM_TRACKING_ID = "fake"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "4.5.6"
    settings.EMAIL_SUPPORT = "support@text.com"
    settings.WEBPACK_USE_DEV_SERVER = False
    settings.RECAPTCHA_SITE_KEY = "fake_key"
    settings.ZENDESK_CONFIG = {
        "HELP_WIDGET_ENABLED": False,
        "HELP_WIDGET_KEY": "fake_key",
    }
    settings.FEATURES["DIGITAL_CREDENTIALS"] = True
    settings.DIGITAL_CREDENTIALS_SUPPORTED_RUNS = "test_run1,test_run2"
    mocker.patch(
        "mitol.olposthog.features.is_enabled",
        side_effect=posthog_is_enabled_side_effect,
    )
    mocker.patch("ecommerce.api.is_tax_applicable", return_value=False)

    request = rf.get("/")
    request.user = user

    assert get_js_settings(request) == {
        "gaTrackingID": "fake",
        "gtmTrackingID": "fake",
        "public_path": "/static/bundles/",
        "environment": settings.ENVIRONMENT,
        "sentry_dsn": remove_password_from_url(os.environ.get("SENTRY_DSN", "")),
        "release_version": settings.VERSION,
        "recaptchaKey": settings.RECAPTCHA_SITE_KEY,
        "support_email": settings.EMAIL_SUPPORT,
        "site_name": settings.SITE_NAME,
        "zendesk_config": {"help_widget_enabled": False, "help_widget_key": "fake_key"},
        "digital_credentials": settings.FEATURES.get("DIGITAL_CREDENTIALS", False),
        "digital_credentials_supported_runs": settings.DIGITAL_CREDENTIALS_SUPPORTED_RUNS,
        "is_tax_applicable": is_tax_applicable(request),
        "enable_enterprise": False,
        "posthog_api_token": settings.POSTHOG_PROJECT_API_KEY,
        "posthog_api_host": settings.POSTHOG_API_HOST,
    }


@pytest.mark.parametrize(
    ("url", "remove_query_params", "expected_url"),
    [
        ("https://test_url.com/?query_param=True", True, "https://test_url.com/"),
        (
            "https://test_url.com/?query_param=True",
            False,
            "https://test_url.com/?query_param=True",
        ),
        (" https://test_url.com/ ?query_param=True ", True, "https://test_url.com/"),
        (
            " https://test_url.com/ ?query_param=True ",
            False,
            "https://test_url.com/?query_param=True",
        ),
        ("   ?query_param=True", True, ""),
        ("   ?query_param=True", False, "?query_param=True"),
    ],
)
def test_clean_url(url, remove_query_params, expected_url):
    """
    Tests that `clean_url` returns the cleaned URL.
    """
    assert clean_url(url, remove_query_params=remove_query_params) == expected_url


@pytest.mark.parametrize(
    ("date_str", "date_format", "date_timezone", "expected_date"),
    [
        (
            "2025-06-26",
            "%Y-%m-%d",
            datetime.UTC,
            datetime.datetime(2025, 6, 26, tzinfo=datetime.UTC),
        ),
        (
            "2025-06-26",
            "%Y-%m-%d",
            None,
            datetime.datetime(2025, 6, 26, tzinfo=datetime.UTC),
        ),
        (
            "21 June, 2018",
            "%d %B, %Y",
            datetime.UTC,
            datetime.datetime(2018, 6, 21, tzinfo=datetime.UTC),
        ),
        (
            "21 June, 2018",
            "%d %B, %Y",
            None,
            datetime.datetime(2018, 6, 21, tzinfo=datetime.UTC),
        ),
        (
            "12/11/2018 09:15:32",
            "%d/%m/%Y %H:%M:%S",
            datetime.UTC,
            datetime.datetime(2018, 11, 12, 9, 15, 32, tzinfo=datetime.UTC),
        ),
        (
            "12/11/2018 09:15:32",
            "%d/%m/%Y %H:%M:%S",
            None,
            datetime.datetime(2018, 11, 12, 9, 15, 32, tzinfo=datetime.UTC),
        ),
    ],
)
def test_strip_datetime(date_str, date_format, date_timezone, expected_date):
    """
    Tests that `strip_datetime` strips the datetime and sets the timezone.
    """
    assert strip_datetime(date_str, date_format, date_timezone) == expected_date
