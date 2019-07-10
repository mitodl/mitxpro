"""Compliance API"""
from collections import namedtuple
import logging

from django.conf import settings
from lxml import etree
from nacl.encoding import Base64Encoder
from nacl.public import PublicKey, SealedBox
from zeep import Client
from zeep.plugins import HistoryPlugin
from zeep.wsse.username import UsernameToken

from compliance.constants import (
    REASON_CODE_SUCCESS,
    EXPORTS_BLOCKED_REASON_CODES,
    TEMPORARY_FAILURE_REASON_CODES,
    RESULT_DENIED,
    RESULT_SUCCESS,
    RESULT_UNKNOWN,
)
from compliance.models import ExportsInquiryLog


log = logging.getLogger()

DecryptedLog = namedtuple("DecryptedLog", ["request", "response"])


EXPORTS_REQUIRED_KEYS = [
    "CYBERSOURCE_WSDL_URL",
    "CYBERSOURCE_MERCHANT_ID",
    "CYBERSOURCE_TRANSACTION_KEY",
    "CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY",
]


def is_exports_verification_enabled():
    """Returns True if the exports verification is configured"""
    return all(getattr(settings, key) for key in EXPORTS_REQUIRED_KEYS)


def get_cybersource_client():
    """
    Configures and authenticates a CyberSource client

    Returns:
        (zeep.Client, zeep.plugins.HistoryPlugin):
            a tuple of the configured client and the history plugin instance
    """
    wsse = UsernameToken(
        settings.CYBERSOURCE_MERCHANT_ID, settings.CYBERSOURCE_TRANSACTION_KEY
    )
    history = HistoryPlugin()
    client = Client(settings.CYBERSOURCE_WSDL_URL, wsse=wsse, plugins=[history])
    return client, history


def compute_result_from_codes(reason_code, info_code):
    """
    Determines the result from the reason and info codes

    Args:
        reason_code (int): the reasonCode returned from CyberSource
        info_code (str): the infoCode returned from CyberSource

    Returns:
        str:
            the computed result
    """
    # if there's either an explicit denial or any block list was triggered
    # NOTE: reason_code can indicate a success but a block list still be triggered and indicated in info_code
    if reason_code in EXPORTS_BLOCKED_REASON_CODES or info_code:
        return RESULT_DENIED

    # a success with no red flags whatsoever
    if reason_code == REASON_CODE_SUCCESS:
        return RESULT_SUCCESS

    # failed to process an unknown reasonCode
    log.error(
        "Unable to verify exports controls, received unknown reasonCode: %s",
        reason_code,
    )
    return RESULT_UNKNOWN


def get_encryption_public_key():
    """Returns the public key for encryption of export requests/responses"""
    return PublicKey(
        settings.CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY, encoder=Base64Encoder
    )


def log_exports_inquiry(user, response, last_sent, last_received):
    """
    Log a request/response for an export inquiry for a given user

    Args:
        user (users.models.User): the user that was checked for exports compliance
        response (etree.Element): the root response node from the API call
        last_sent (dict): the raw request sent for this call
        last_received (dict): the raw response received for this call

    Returns:
        ExportsInquiryLog: the generated log record of the exports inquiry
    """
    # render lxml data structures into a string so we can encrypt it
    xml_request = etree.tostring(last_sent["envelope"])
    xml_response = etree.tostring(last_received["envelope"])

    log.debug("Sent: %s", xml_request)
    log.debug("Received: %s", xml_response)

    # overall status code of the response
    # NOTE: reason_code can indicate a success but a block list still be triggered and indicated in info_code
    reason_code = int(response.reasonCode)

    if reason_code in TEMPORARY_FAILURE_REASON_CODES:
        # if it's a temporary failure in the CyberSource backend or
        # the request itself, no point in recording this
        log.error(
            "Unable to verify exports controls, received reasonCode: %s", reason_code
        )
        return None

    # if the data triggered a block list this will be truthy
    info_code = response.exportReply.infoCode

    box = SealedBox(get_encryption_public_key())
    encrypted_request = box.encrypt(xml_request, encoder=Base64Encoder).decode("ascii")
    encrypted_response = box.encrypt(xml_response, encoder=Base64Encoder).decode(
        "ascii"
    )

    return ExportsInquiryLog.objects.create(
        user=user,
        computed_result=compute_result_from_codes(reason_code, info_code),
        reason_code=reason_code,
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
    Create an address appropriate to pass to billTo on the CyberSource API

    Args:
        user (users.models.User): the user whose address to use

    Returns:
        dict:
            User's legal_address in the appropriate data structure
    """

    legal_address = user.legal_address

    # minimally require fields
    billing_address = {
        "firstName": legal_address.first_name,
        "lastName": legal_address.last_name,
        "email": user.email,
        "street1": legal_address.street_address_1,
        "street2": legal_address.street_address_2,
        "street3": legal_address.street_address_3,
        "street4": legal_address.street_address_4,
        "city": legal_address.city,
        "country": legal_address.country,
    }

    # these are required for certain countries, we presume here that data was validated before it was written
    if legal_address.state_or_territory:
        # State is in US-MA format and we want that send part
        billing_address["state"] = legal_address.state_or_territory.split("-")[1]

    if legal_address.postal_code:
        billing_address["postalCode"] = legal_address.postal_code

    return billing_address


def verify_user_with_exports(user):
    """Verify the user against the CyberSource exports service"""
    client, history = get_cybersource_client()

    payload = {
        "merchantID": settings.CYBERSOURCE_MERCHANT_ID,
        "merchantReferenceCode": user.id,
        "billTo": get_bill_to_address(user),
        "exportService": {
            "run": "true",  # NOTE: *must* be a string otherwise it will serialize incorrectly to "True"
            "addressOperator": settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR,
            "addressWeight": settings.CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT,
            "nameWeight": settings.CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT,
        },
    }

    sanctions_lists = settings.CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS

    if sanctions_lists:
        payload["exportService"]["sanctionsLists"] = sanctions_lists

    response = client.service.runTransaction(**payload)

    return log_exports_inquiry(user, response, history.last_sent, history.last_received)


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
