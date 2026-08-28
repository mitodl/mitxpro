"""Tests for compliance api"""

import json
import time

import pytest
from CyberSource.rest import ApiException
from nacl.encoding import Base64Encoder
from nacl.public import SealedBox

from compliance import api
from compliance.constants import (
    DECISION_COMPLETED,
    DECISION_DECLINED,
    DECISION_INVALID_REQUEST,
    RESULT_DENIED,
    RESULT_SUCCESS,
    RESULT_UNKNOWN,
    TEMPORARY_FAILURE_DECISIONS,
)
from compliance.factories import ExportsInquiryLogFactory
from compliance.models import ExportsInquiryLog
from compliance.test_utils import make_cybersource_response


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
    """Test that decrypt_exports_inquiry can decrypt an encrypted log"""
    request = b'{"sent": true}'
    response = b'{"received": true}'

    box = SealedBox(cybersource_private_key)

    log = mocker.Mock()
    log.encrypted_request = box.encrypt(request, encoder=Base64Encoder)
    log.encrypted_response = box.encrypt(response, encoder=Base64Encoder)

    decrypted = api.decrypt_exports_inquiry(log, cybersource_private_key)

    assert decrypted.request == request
    assert decrypted.response == response


@pytest.mark.usefixtures("cybersource_settings")
def test_log_exports_inquiry(cybersource_private_key, user):
    """Test that log_exports_inquiry correctly stores the result"""
    request_payload = '{"sent": true}'
    response = make_cybersource_response(DECISION_COMPLETED, ["MATCH-BCO"])

    log = api.log_exports_inquiry(user, request_payload, response)

    assert log.user == user
    assert log.reason_code == DECISION_COMPLETED
    assert log.info_code == "MATCH-BCO"
    assert log.computed_result == RESULT_DENIED

    decrypted = api.decrypt_exports_inquiry(log, cybersource_private_key)

    assert decrypted.request == b'{"sent": true}'
    assert json.loads(decrypted.response)["status"] == DECISION_COMPLETED


@pytest.mark.parametrize(
    "cybersource_mock_client_responses, expected_result",  # noqa: PT006
    [
        [(DECISION_DECLINED, None), RESULT_DENIED],  # noqa: PT007
        [(DECISION_COMPLETED, ["MATCH-BCO"]), RESULT_DENIED],  # noqa: PT007
        [(DECISION_COMPLETED, None), RESULT_SUCCESS],  # noqa: PT007
        [("SOMETHING_ELSE", None), RESULT_UNKNOWN],  # noqa: PT007
    ],
    indirect=["cybersource_mock_client_responses"],
)
def test_verify_user_with_exports(
    user, cybersource_mock_client_responses, expected_result
):
    """Test that verify_user_with_exports computes and records each decision"""
    result = api.verify_user_with_exports(user)

    assert result.computed_result == expected_result

    assert ExportsInquiryLog.objects.filter(user=user).exists()


def test_verify_user_with_exports_sends_expected_payload(user, cybersource_mock_client):
    """The REST payload should carry the user's identity and legal address"""
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(DECISION_COMPLETED)
    )

    api.verify_user_with_exports(user)

    cybersource_mock_client.validate_export_compliance.assert_called_once()
    payload = json.loads(
        cybersource_mock_client.validate_export_compliance.call_args.args[0]
    )
    bill_to = payload["order_information"]["bill_to"]

    assert payload["client_reference_information"]["code"] == str(user.id)
    assert bill_to["email"] == user.email
    assert bill_to["first_name"] == user.legal_address.first_name
    assert bill_to["last_name"] == user.legal_address.last_name
    assert bill_to["locality"] == user.legal_address.city
    assert bill_to["country"] == user.legal_address.country
    # empty optional fields are stripped rather than sent as null
    assert None not in bill_to.values()


def test_verify_user_with_exports_unwraps_tuple_response(user, cybersource_mock_client):
    """Some SDK calls return (body, status, headers) rather than just the body"""
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(DECISION_COMPLETED),
        200,
        {},
    )

    result = api.verify_user_with_exports(user)

    assert result.computed_result == RESULT_SUCCESS


@pytest.mark.usefixtures("cybersource_settings")
def test_verify_user_with_exports_without_legal_address(
    mocker, user, cybersource_mock_client
):
    """A user with no legal address is screened on email alone rather than erroring"""
    mocker.patch.object(
        type(user),
        "legal_address",
        property(lambda self: (_ for _ in ()).throw(api.ObjectDoesNotExist())),
    )
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(DECISION_INVALID_REQUEST)
    )

    assert api.verify_user_with_exports(user) is None

    payload = json.loads(
        cybersource_mock_client.validate_export_compliance.call_args.args[0]
    )
    assert payload["order_information"]["bill_to"] == {"email": user.email}


@pytest.mark.parametrize("decision", TEMPORARY_FAILURE_DECISIONS)
def test_verify_user_with_exports_temporary_errors(
    mocker, user, cybersource_mock_client, decision
):
    """Verify no result is recorded if the nature of the error is temporary"""
    mock_log = mocker.patch("compliance.api.log")
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(decision)
    )

    assert api.verify_user_with_exports(user) is None
    mock_log.error.assert_called_once_with(
        "Unable to verify exports controls, received status: %s", decision
    )

    assert not ExportsInquiryLog.objects.filter(user=user).exists()


@pytest.mark.parametrize(
    ("sanctions_lists", "expected"),
    [([], None), (["OFAC"], ["OFAC"]), (["OFAC", "EU"], ["OFAC", "EU"])],
)
def test_verify_user_with_exports_sanctions_lists(
    user, cybersource_settings, cybersource_mock_client, sanctions_lists, expected
):
    """Verify the sanctions list is passed only if it is configured"""
    cybersource_settings.CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS = sanctions_lists
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(DECISION_COMPLETED)
    )

    api.verify_user_with_exports(user)

    payload = json.loads(
        cybersource_mock_client.validate_export_compliance.call_args.args[0]
    )
    assert payload["export_compliance_information"].get("sanction_lists") == expected


def test_verify_user_with_exports_screening_weights(
    user, cybersource_settings, cybersource_mock_client
):
    """The configured operator and weights are sent on every request"""
    cybersource_settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR = "OR"
    cybersource_settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT = "low"
    cybersource_settings.CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT = "medium"
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(DECISION_COMPLETED)
    )

    api.verify_user_with_exports(user)

    payload = json.loads(
        cybersource_mock_client.validate_export_compliance.call_args.args[0]
    )
    export_info = payload["export_compliance_information"]
    assert export_info["address_operator"] == "OR"
    assert export_info["weights"] == {"address": "low", "name": "medium"}


def _api_exception(status, body):
    """Build an ApiException carrying a raw response body"""
    exc = ApiException(status=status)
    exc.body = body
    return exc


def test_verify_user_with_exports_error_carrying_a_decision(
    user, cybersource_mock_client
):
    """A 4xx whose body holds a decision is handled, not raised"""
    cybersource_mock_client.validate_export_compliance.side_effect = _api_exception(
        400,
        json.dumps(
            {
                "status": DECISION_INVALID_REQUEST,
                "reason": "MISSING_FIELD",
                "details": [{"field": "orderInformation.billTo.country"}],
            }
        ).encode("utf-8"),
    )

    assert api.verify_user_with_exports(user) is None
    assert not ExportsInquiryLog.objects.filter(user=user).exists()


@pytest.mark.parametrize(
    "body",
    [
        b'{"message": "Authentication Failed"}',  # no decision in it
        b"not json at all",
        b"",
        None,
    ],
)
def test_verify_user_with_exports_error_without_a_decision(
    user, cybersource_mock_client, body
):
    """Errors with no decision keep propagating rather than becoming a silent None"""
    cybersource_mock_client.validate_export_compliance.side_effect = _api_exception(
        401, body
    )

    with pytest.raises(ApiException):
        api.verify_user_with_exports(user)

    assert not ExportsInquiryLog.objects.filter(user=user).exists()


def test_get_latest_export_inquiry(user):
    """Test that get_latest_export_inquiry returns the latest log entry"""
    log1 = ExportsInquiryLogFactory.create(user=user)
    time.sleep(1)  # ensure there's a difference in created_on
    log2 = ExportsInquiryLogFactory.create(user=user)

    assert log2.created_on > log1.created_on
    assert api.get_latest_exports_inquiry(user) == log2
