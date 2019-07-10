"""Tests for compliance api"""

# pylint: disable=redefined-outer-name
import time

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
from compliance.factories import ExportsInquiryLogFactory
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


def test_decrypt_exports_inquiry(mocker, cybersource_private_key):
    """Test that decrypt_exports_inquiry can decrypted an encrypted log"""
    request = b"<sent/>"
    response = b"<received/>"

    box = SealedBox(cybersource_private_key)

    log = mocker.Mock()
    log.encrypted_request = box.encrypt(request, encoder=Base64Encoder)
    log.encrypted_response = box.encrypt(response, encoder=Base64Encoder)

    decrypted = api.decrypt_exports_inquiry(log, cybersource_private_key)

    assert decrypted.request == request
    assert decrypted.response == response


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

    decrypted = api.decrypt_exports_inquiry(log, cybersource_private_key)

    assert decrypted.request == b"<sent/>"
    assert decrypted.response == b"<received/>"


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


def test_get_latest_export_inquiry(user):
    """Test that get_latest_export_inquiry returns the latest log entry"""
    log1 = ExportsInquiryLogFactory.create(user=user)
    time.sleep(1)  # ensure there's a difference in created_on
    log2 = ExportsInquiryLogFactory.create(user=user)

    assert log2.created_on > log1.created_on
    assert api.get_latest_exports_inquiry(user) == log2
