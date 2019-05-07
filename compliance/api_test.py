"""Tests for compliance api"""

# pylint: disable=redefined-outer-name
import pytest
from lxml import etree

from compliance import api
from compliance.constants import (
    RESULT_SUCCESS,
    RESULT_DENIED,
    RESULT_UNKNOWN,
    TEMPORARY_FAILURE_REASON_CODES,
)


@pytest.mark.usefixtures("cybersource_settings")
def test_is_exports_verification_enabled():
    """Test that is_exports_verification_enabled is true if all settings set"""
    assert api.is_exports_verification_enabled() is True


@pytest.mark.usefixtures("cybersource_settings")
@pytest.mark.parametrize("key", api.EXPORTS_REQUIRED_KEYS)
def test_is_exports_verification_disabled(settings, key):
    """Test that is_exports_verification_enabled is false if a setting is missing"""
    setattr(settings, key, None)
    assert api.is_exports_verification_enabled() is False


@pytest.mark.parametrize(
    "cybersource_mock_client_responses, expected_result",
    [
        ["700_reject", RESULT_DENIED],
        ["100_success_match", RESULT_DENIED],
        ["100_success", RESULT_SUCCESS],
        ["978_unknown", RESULT_UNKNOWN],
    ],
    indirect=["cybersource_mock_client_responses"],
)
def test_verify_user_with_exports(
    user, cybersource_mock_client_responses, expected_result
):  # pylint: disable=unused-argument
    """Test that verify_user_with_exports handles"""
    result = api.verify_user_with_exports(user)

    assert result.computed_result == expected_result


@pytest.mark.usefixtures("cybersource_settings")
@pytest.mark.parametrize("reason_code", TEMPORARY_FAILURE_REASON_CODES)
def test_verify_user_with_exports_temporary_errors(mocker, user, reason_code):
    """Verify no result is recorded if the nature of the error is temporary"""
    mock_log = mocker.patch("compliance.api.log")
    #
    mock_client = mocker.Mock()
    mock_client.service.runTransaction.return_value.reasonCode = str(reason_code)
    # create a history with some dummy lxml objects
    mock_history = mocker.Mock(
        last_sent={"envelope": etree.Element("sent")},
        last_received={"envelope": etree.Element("received")},
    )
    with mocker.patch(
        "compliance.api.get_cybersource_client",
        return_value=(mock_client, mock_history),
    ):
        assert api.verify_user_with_exports(user) is None
    mock_log.error.assert_called_once_with(
        "Unable to verify exports controls, received reasonCode: %s", reason_code
    )
