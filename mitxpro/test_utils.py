"""Testing utils"""
import abc
import json
from contextlib import contextmanager
import traceback
from unittest.mock import Mock
import csv
import tempfile

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.renderers import JSONRenderer
from requests.exceptions import HTTPError


def any_instance_of(*cls):
    """
    Returns a type that evaluates __eq__ in isinstance terms

    Args:
        cls (list of types): variable list of types to ensure equality against

    Returns:
        AnyInstanceOf: dynamic class type with the desired equality
    """

    class AnyInstanceOf(metaclass=abc.ABCMeta):
        """Dynamic class type for __eq__ in terms of isinstance"""

        def __eq__(self, other):
            return isinstance(other, cls)

    for c in cls:
        AnyInstanceOf.register(c)
    return AnyInstanceOf()


@contextmanager
def assert_not_raises():
    """Used to assert that the context does not raise an exception"""
    try:
        yield
    except AssertionError:
        raise
    except Exception:  # pylint: disable=broad-except
        pytest.fail(f"An exception was not raised: {traceback.format_exc()}")


def assert_drf_json_equal(obj1, obj2):
    """
    Asserts that two objects are equal after a round trip through JSON serialization/deserialization.
    Particularly helpful when testing DRF serializers where you may get back OrderedDict and other such objects.

    Args:
        obj1 (object): the first object
        obj2 (object): the second object
    """
    json_renderer = JSONRenderer()
    converted1 = json.loads(json_renderer.render(obj1))
    converted2 = json.loads(json_renderer.render(obj2))
    assert converted1 == converted2


class MockResponse:
    """
    Mock requests.Response
    """

    def __init__(
        self, content, status_code=200, content_type="application/json", url=None
    ):
        if isinstance(content, (dict, list)):
            self.content = json.dumps(content)
        else:
            self.content = str(content)
        self.text = self.content
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        if url:
            self.url = url

    def json(self):
        """ Return json content"""
        return json.loads(self.content)


class MockHttpError(HTTPError):
    """Mocked requests.exceptions.HttpError"""

    def __init__(self, *args, **kwargs):
        response = MockResponse(content={"bad": "response"}, status_code=400)
        super().__init__(*args, **{**kwargs, **{"response": response}})


def drf_datetime(dt):
    """
    Returns a datetime formatted as a DRF DateTimeField formats it

    Args:
        dt(datetime): datetime to format

    Returns:
        str: ISO 8601 formatted datetime
    """
    return dt.isoformat().replace("+00:00", "Z")


class PickleableMock(Mock):
    """
    A Mock that can be passed to pickle.dumps()

    Source: https://github.com/testing-cabal/mock/issues/139#issuecomment-122128815
    """

    def __reduce__(self):
        """Required method for being pickleable"""
        return (Mock, ())


def create_tempfile_csv(rows_iter):
    """
    Creates a temporary CSV file for use in testing file upload views

    Args:
        rows_iter (iterable of lists): An iterable of lists of strings representing the csv values.
            Example: [["a","b","c"], ["d","e","f"]] --> CSV contents: "a,b,c\nd,e,f"

    Returns:
        SimpleUploadedFile: A temporary CSV file with the given contents
    """
    f = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    with open(f.name, "w", encoding="utf8", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        for row in rows_iter:
            writer.writerow(row)
    with open(f.name, "r") as user_csv:
        return SimpleUploadedFile(
            f.name, user_csv.read().encode("utf8"), content_type="application/csv"
        )


def format_as_iso8601(time):
    """Helper function to format datetime with the Z at the end"""
    # Can't use datetime.isoformat() because format is slightly different from this
    iso_format = "%Y-%m-%dT%H:%M:%S"
    formatted_time = time.strftime(iso_format)
    if time.microsecond:
        miniseconds_format = ".%f"
        formatted_time += time.strftime(miniseconds_format)[:4]
    return formatted_time + "Z"


def list_of_dicts(specialty_dict_iter):
    """
    Some library methods yield an OrderedDict or defaultdict, and it's easier to confirm their contents using a
    regular dict. This function turns an iterable of specialty dicts into a list of normal dicts.

    Args:
        specialty_dict_iter:

    Returns:
        list of dict: A list of dicts
    """
    return list(map(dict, specialty_dict_iter))


def set_request_session(request, session_dict):
    """
    Sets session variables on a RequestFactory object
    Args:
        request (WSGIRequest): A RequestFactory-produced request object (from RequestFactory.get(), et. al.)
        session_dict (dict): Key/value pairs of session variables to set

    Returns:
        RequestFactory: The same request object with session variables set
    """
    middleware = SessionMiddleware()
    middleware.process_request(request)
    for key, value in session_dict.items():
        request.session[key] = value
    request.session.save()
    return request


def update_namespace(tuple_to_update, **updates):
    """
    Returns a new namespace with the same properties as the input, but updated with
    the given kwargs.

    Args:
        tuple_to_update (Union([types.namedtuple, typing.NamedTuple])): The tuple object
        **updates: Properties to update on the tuple

    Returns:
        Union([types.namedtuple, typing.NamedTuple]): The updated namespace
    """
    return tuple_to_update.__class__(
        **{  # pylint: disable=protected-access
            **tuple_to_update._asdict(),  # pylint: disable=protected-access
            **updates,
        }
    )
