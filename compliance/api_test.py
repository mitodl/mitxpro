"""Tests for compliance api"""

# pylint: disable=redefined-outer-name
import pytest
from lxml import etree
from nacl.encoding import Base64Encoder
from nacl.public import SealedBox

from compliance import api
from compliance.constants import (
    RESULT_SUCCESS,
    RESULT_DENIED,
    RESULT_UNKNOWN,
    TEMPORARY_FAILURE_REASON_CODES,
)
from compliance.models import ExportsInquiryLog


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


@pytest.mark.usefixtures("cybersource_settings")
def test_log_exports_inquiry(mocker, cybersource_private_key, user):
    """Test that log_exports_inquiry correctly stores the result"""
    last_sent = {"envelope": etree.Element("sent")}
    last_received = {"envelope": etree.Element("received")}
    mock_response = mocker.Mock(
        reasonCode="100", exportReply=mocker.Mock(infoCode="102")
    )
    log = api.log_exports_inquiry(user, mock_response, last_sent, last_received)

    assert log.user == user
    assert log.reason_code == 100
    assert log.info_code == "102"

    box = SealedBox(cybersource_private_key)

    assert box.decrypt(log.encrypted_request, encoder=Base64Encoder) == b"<sent/>"
    assert box.decrypt(log.encrypted_response, encoder=Base64Encoder) == b"<received/>"


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

    assert ExportsInquiryLog.objects.filter(user=user).exists()


@pytest.mark.usefixtures("cybersource_settings")
@pytest.mark.parametrize("reason_code", TEMPORARY_FAILURE_REASON_CODES)
def test_verify_user_with_exports_temporary_errors(mocker, user, reason_code):
    """Verify no result is recorded if the nature of the error is temporary"""
    mock_log = mocker.patch("compliance.api.log")

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

    assert not ExportsInquiryLog.objects.filter(user=user).exists()


@pytest.mark.parametrize(
    "sanctions_lists, expect_passed", [[None, False], ["", False], ["OFAC", True]]
)
def test_verify_user_with_exports_sanctions_lists(
    mocker, user, cybersource_settings, sanctions_lists, expect_passed
):
    """Verify the sanctions list is passed only if it is configured"""
    cybersource_settings.CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS = sanctions_lists

    mock_client = mocker.Mock()
    mock_client.service.runTransaction.return_value.reasonCode = "100"
    mock_client.service.runTransaction.return_value.exportReply.infoCode = 100
    # create a history with some dummy lxml objects
    mock_history = mocker.Mock(
        last_sent={"envelope": etree.Element("sent")},
        last_received={"envelope": etree.Element("received")},
    )
    with mocker.patch(
        "compliance.api.get_cybersource_client",
        return_value=(mock_client, mock_history),
    ):
        api.verify_user_with_exports(user)

    payload = mock_client.service.runTransaction.call_args[1]

    if expect_passed:
        assert payload["exportService"]["sanctionsLists"] == sanctions_lists
    else:
        assert "sanctionsLists" not in payload["exportService"]
