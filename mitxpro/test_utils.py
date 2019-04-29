"""Testing utils"""
import abc
import json
from contextlib import contextmanager
import traceback
from unittest.mock import Mock
import csv
import tempfile

import pytest

from django.core.files.uploadedfile import SimpleUploadedFile


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


class MockResponse:
    """
    Mock requests.Response
    """

    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code

    def json(self):
        """ Return content as json """
        return json.loads(self.content)


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
