"""Compliance API"""

import json
import logging
from collections import namedtuple

from CyberSource.api.verification_api import VerificationApi
from CyberSource.models.riskv1exportcomplianceinquiries_order_information import (
    Riskv1exportcomplianceinquiriesOrderInformation,
)
from CyberSource.models.riskv1exportcomplianceinquiries_order_information_bill_to import (
    Riskv1exportcomplianceinquiriesOrderInformationBillTo,
)
from CyberSource.models.ptsv2payments_watchlist_screening_information_weights import (
    Ptsv2paymentsWatchlistScreeningInformationWeights,
)
from CyberSource.models.risk_v1_decisions_post201_response_client_reference_information import (
    RiskV1DecisionsPost201ResponseClientReferenceInformation,
)
from CyberSource.models.riskv1exportcomplianceinquiries_export_compliance_information import (
    Riskv1exportcomplianceinquiriesExportComplianceInformation,
)
from CyberSource.models.validate_export_compliance_request import (
    ValidateExportComplianceRequest,
)
from CyberSource.rest import ApiException
from django.conf import settings
from nacl.encoding import Base64Encoder
from nacl.public import PublicKey, SealedBox

from compliance.constants import (
    DECISION_COMPLETED,
    DENIED_DECISIONS,
    RESULT_DENIED,
    RESULT_SUCCESS,
    RESULT_UNKNOWN,
    TEMPORARY_FAILURE_DECISIONS,
)
from compliance.models import ExportsInquiryLog

log = logging.getLogger()

DecryptedLog = namedtuple("DecryptedLog", ["request", "response"])  # noqa: PYI024

# This call sits in the synchronous login and registration path, so a hung
# connection would hold a worker. The SDK only honours a per-request value;
# a `timeout` key in the client config is silently ignored.
EXPORTS_REQUEST_TIMEOUT_SECONDS = 10

# only a 4xx carries a decision; 5xx and auth failures are outages
HTTP_BAD_REQUEST = 400
HTTP_SERVER_ERROR = 500


EXPORTS_REQUIRED_KEYS = [
    "CYBERSOURCE_REST_MERCHANT_ID",
    "CYBERSOURCE_REST_KEY_ID",
    "CYBERSOURCE_REST_SECRET",
    "CYBERSOURCE_REST_ENVIRONMENT",
    "CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY",
]


def is_exports_verification_enabled():
    """Returns True if the exports verification is configured"""
    return all(getattr(settings, key) for key in EXPORTS_REQUIRED_KEYS)


def get_cybersource_client():
    """
    Configures and authenticates a CyberSource REST client

    Returns:
        CyberSource.api.verification_api.VerificationApi:
            the configured client for the export compliance service
    """
    return VerificationApi(
        {
            "authentication_type": "HTTP_SIGNATURE",
            "merchantid": settings.CYBERSOURCE_REST_MERCHANT_ID,
            "merchant_keyid": settings.CYBERSOURCE_REST_KEY_ID,
            "merchant_secretkey": settings.CYBERSOURCE_REST_SECRET,
            "run_environment": settings.CYBERSOURCE_REST_ENVIRONMENT,
        }
    )


def compute_result_from_codes(decision, info_code):
    """
    Determines the result from the decision and info codes

    Args:
        decision (str): the status returned from CyberSource
        info_code (str): the comma-separated infoCodes returned from CyberSource

    Returns:
        str:
            the computed result
    """
    # if there's either an explicit denial or any sanctions list was matched
    # NOTE: a decision can be COMPLETED but a match still be reported in infoCodes
    if decision in DENIED_DECISIONS or info_code:
        return RESULT_DENIED

    # a completed screening with no matches whatsoever
    if decision == DECISION_COMPLETED:
        return RESULT_SUCCESS

    # failed to process an unknown decision
    log.error(
        "Unable to verify exports controls, received unknown status: %s",
        decision,
    )
    return RESULT_UNKNOWN


def get_encryption_public_key():
    """Returns the public key for encryption of export requests/responses"""
    return PublicKey(
        settings.CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY, encoder=Base64Encoder
    )


def get_response_value(response, *names):
    """
    Read a value from an SDK response object or dict using any of the given names

    The SDK returns snake_case attributes on model objects but the raw wire format
    is camelCase, and some calls hand back a plain dict, so both are accepted.

    Args:
        response: an SDK response object or dict
        *names (str): the candidate attribute/key names

    Returns:
        the first value found, or None
    """
    if response is None:
        return None

    if isinstance(response, dict):
        for name in names:
            value = response.get(name)
            if value is not None:
                return value
        return None

    for name in names:
        value = getattr(response, name, None)
        if value is not None:
            return value

    return None


def get_info_code(response):
    """
    Extract the sanctions-list match codes from a response

    Args:
        response: the response returned from CyberSource

    Returns:
        str or None: the comma-separated infoCodes, or None if there were no matches
    """
    export_info = get_response_value(
        response,
        "export_compliance_information",
        "exportComplianceInformation",
    )
    info_codes = get_response_value(export_info, "info_codes", "infoCodes")
    return ",".join(info_codes) if info_codes else None


def remove_none_values(value):
    """
    Recursively drop None values from an SDK payload

    Args:
        value: a dict, list or scalar from ``to_dict()``

    Returns:
        the same structure with None values removed
    """
    if isinstance(value, dict):
        return {
            key: remove_none_values(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [remove_none_values(item) for item in value if item is not None]
    return value


def parse_api_error(exc):
    """
    Decode the response body carried by an ApiException

    CyberSource answers a request it cannot process - missing bill-to fields,
    an unrecognised country - with a 4xx whose body holds the same decision
    shape as a normal response. Everything else (auth failures, outages) has no
    decision in it and should keep propagating.

    Args:
        exc (CyberSource.rest.ApiException): the raised exception

    Returns:
        dict or None: the decoded body, or None if it holds no decision
    """
    status_code = getattr(exc, "status", None)
    if status_code is None or not HTTP_BAD_REQUEST <= status_code < HTTP_SERVER_ERROR:
        return None

    body = getattr(exc, "body", None)
    if not body:
        return None
    try:
        decoded = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    except ValueError:
        return None
    return decoded if get_response_value(decoded, "status") else None


def serialize_response(response):
    """
    Render a CyberSource response as the JSON text to store in the audit log

    Args:
        response: the response returned from CyberSource

    Returns:
        str: the serialized response
    """
    if hasattr(response, "to_dict"):
        response = response.to_dict()
    return json.dumps(response, default=str)


def log_exports_inquiry(user, request_payload, response):
    """
    Log a request/response for an export inquiry for a given user

    Args:
        user (users.models.User): the user that was checked for exports compliance
        request_payload (str): the raw request sent for this call
        response: the response received for this call

    Returns:
        ExportsInquiryLog: the generated log record of the exports inquiry, or None
            if the failure was temporary and shouldn't be recorded
    """
    decision = get_response_value(response, "status")

    log.debug("Sent: %s", request_payload)
    log.debug("Received: %s", response)

    if decision in TEMPORARY_FAILURE_DECISIONS:
        # if it's a temporary failure in the CyberSource backend or
        # the request itself, no point in recording this
        log.error(
            "Unable to verify exports controls for user %s: status=%s reason=%s details=%s",
            user.id,
            decision,
            get_response_value(response, "reason"),
            get_response_value(response, "details"),
        )
        return None

    # if the data matched a sanctions list this will be truthy
    info_code = get_info_code(response)

    box = SealedBox(get_encryption_public_key())
    encrypted_request = box.encrypt(
        request_payload.encode("utf-8"), encoder=Base64Encoder
    ).decode("ascii")
    encrypted_response = box.encrypt(
        serialize_response(response).encode("utf-8"), encoder=Base64Encoder
    ).decode("ascii")

    return ExportsInquiryLog.objects.create(
        user=user,
        computed_result=compute_result_from_codes(decision, info_code),
        reason_code=decision or "",
        info_code=info_code,
        encrypted_request=encrypted_request,
        encrypted_response=encrypted_response,
    )


def decrypt_exports_inquiry(exports_inquiry_log, private_key):
    """
    Decrypts an exports inquiry log given a private key

    Arguments:
        exports_inquiry_log (ExportsInquiryLog):
            log record to decrypt
        private_key (nacl.public.PrivateKey):
            the private key to decrypt the request/response with

    Returns:
        DecryptedLog:
            the decrypted request and response
    """
    box = SealedBox(private_key)

    decrypted_request = box.decrypt(
        exports_inquiry_log.encrypted_request, encoder=Base64Encoder
    )
    decrypted_response = box.decrypt(
        exports_inquiry_log.encrypted_response, encoder=Base64Encoder
    )

    return DecryptedLog(decrypted_request, decrypted_response)


def get_bill_to_address(user):
    """
    Create the bill-to fields for the CyberSource export compliance request

    Args:
        user (users.models.User): the user whose address to use

    Returns:
        dict:
            User's legal_address in the appropriate data structure
    """
    legal_address = user.legal_address

    # minimally required fields
    billing_address = {
        "first_name": legal_address.first_name,
        "last_name": legal_address.last_name,
        "email": user.email,
        "address1": legal_address.street_address_1,
        "address2": legal_address.street_address_2,
        "address3": legal_address.street_address_3,
        "address4": legal_address.street_address_4,
        "locality": legal_address.city,
        "country": legal_address.country,
    }

    # these are required for certain countries, we presume here that data was validated before it was written
    if legal_address.state_or_territory:
        # State is in US-MA format and we want that second part
        billing_address["administrative_area"] = legal_address.state_or_territory.split(
            "-"
        )[1]

    if legal_address.postal_code:
        billing_address["postal_code"] = legal_address.postal_code

    # the SDK serializes None into the payload, so drop the empty fields
    return {key: value for key, value in billing_address.items() if value}


def build_export_compliance_information():
    """
    Build the screening parameters for an export compliance request

    These are the REST equivalents of the SOAP exportService fields, so the
    configured operator, weights and sanctions lists carry over unchanged.

    Returns:
        Riskv1exportcomplianceinquiriesExportComplianceInformation: the parameters
    """
    return Riskv1exportcomplianceinquiriesExportComplianceInformation(
        address_operator=settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR,
        weights=Ptsv2paymentsWatchlistScreeningInformationWeights(
            address=settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT,
            name=settings.CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT,
        ),
        # only send this when configured, otherwise CyberSource uses the
        # sanctions lists enabled on the merchant profile
        sanction_lists=settings.CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS or None,
    )


def build_export_payload(user):
    """
    Build the CyberSource export compliance REST request

    Args:
        user (users.models.User): the user to screen

    Returns:
        ValidateExportComplianceRequest: the request to send
    """
    return ValidateExportComplianceRequest(
        client_reference_information=RiskV1DecisionsPost201ResponseClientReferenceInformation(
            code=str(user.id)
        ),
        order_information=Riskv1exportcomplianceinquiriesOrderInformation(
            bill_to=Riskv1exportcomplianceinquiriesOrderInformationBillTo(
                **get_bill_to_address(user)
            )
        ),
        export_compliance_information=build_export_compliance_information(),
    )


def verify_user_with_exports(user):
    """Verify the user against the CyberSource exports service"""
    # A user with no legal address can't be screened at all, and CyberSource
    # rejects a bill-to carrying only an email. Don't spend a request learning
    # that. Django's RelatedObjectDoesNotExist subclasses AttributeError, which
    # is what makes hasattr the right question here.
    if not hasattr(user, "legal_address"):
        log.error(
            "Unable to verify exports controls for user %s: no legal address on file",
            user.id,
        )
        return None

    client = get_cybersource_client()

    payload = build_export_payload(user)
    # this SDK build takes the request as a JSON string, and serializes None
    # values into it unless they're stripped first
    request_payload = json.dumps(remove_none_values(payload.to_dict()), default=str)

    try:
        response = client.validate_export_compliance(
            request_payload, _request_timeout=EXPORTS_REQUEST_TIMEOUT_SECONDS
        )
    except ApiException as exc:
        # a request CyberSource can't process comes back as a 4xx with the
        # decision in the body rather than as a normal response, so treat it
        # like any other non-success decision instead of an error
        response = parse_api_error(exc)
        if response is None:
            raise

    # some SDK calls hand back (body, status, raw) rather than just the body
    if isinstance(response, tuple) and response:
        response = response[0]

    return log_exports_inquiry(user, request_payload, response)


def get_latest_exports_inquiry(user):
    """
    Returns the latest exports inquiry for the user

    Args:
        user (User): the user to find the ExportsInquiryLog for

    Returns:
        ExportsInquiryLog:
            the latest record sorted by created_on
    """
    return user.exports_inquiries.order_by("-created_on").first()
