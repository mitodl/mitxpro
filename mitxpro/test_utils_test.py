"""Tests for test utils"""
import pickle

import pytest

from mitxpro.test_utils import (
    any_instance_of,
    assert_not_raises,
    MockResponse,
    PickleableMock,
    assert_drf_json_equal,
)


def test_any_instance_of():
    """Tests any_instance_of()"""
    any_number = any_instance_of(int, float)

    assert any_number == 0.405
    assert any_number == 8_675_309
    assert any_number != "not a number"
    assert any_number != {}
    assert any_number != []


def test_assert_not_raises_none():
    """
    assert_not_raises should do nothing if no exception is raised
    """
    with assert_not_raises():
        pass


def test_assert_not_raises_exception(mocker):
    """assert_not_raises should fail the test"""
    # Here there be dragons
    fail_mock = mocker.patch("pytest.fail", autospec=True)
    with assert_not_raises():
        raise TabError()
    assert fail_mock.called is True


def test_assert_not_raises_failure():
    """assert_not_raises should reraise an AssertionError"""
    with pytest.raises(AssertionError):
        with assert_not_raises():
            assert 1 == 2


def test_assert_drf_json_equall():
    """Asserts that objects are equal in JSON"""
    assert_drf_json_equal({"a": 1}, {"a": 1})
    assert_drf_json_equal(2, 2)
    assert_drf_json_equal([2], [2])


@pytest.mark.parametrize(
    "content,expected_content,expected_json",
    [
        ['{"test": "content"}', '{"test": "content"}', {"test": "content"}],
        [{"test": "content"}, '{"test": "content"}', {"test": "content"}],
        [["test", "content"], '["test", "content"]', ["test", "content"]],
        [123, "123", 123],
    ],
)
def test_mock_response(content, expected_content, expected_json):
    """ assert MockResponse returns correct values """
    response = MockResponse(content, 404)
    assert response.status_code == 404
    assert response.content == expected_content
    assert response.json() == expected_json


def test_pickleable_mock():
    """Tests that a mock can be pickled"""
    pickle.dumps(PickleableMock(field_name=dict()))
