"""Testing utils around CyberSource"""

from types import SimpleNamespace

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey


def get_cybersource_test_settings(private_key=None):
    """
    Generates a valid set of settings for CyberSource
    """
    if private_key is None:
        private_key = PrivateKey.generate()

    return {
        "CYBERSOURCE_REST_MERCHANT_ID": "merchant_id",
        "CYBERSOURCE_REST_KEY_ID": "key_id",
        "CYBERSOURCE_REST_SECRET": "secret",  # pragma: allowlist secret
        "CYBERSOURCE_REST_ENVIRONMENT": "apitest.cybersource.com",
        "CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY": Base64Encoder.encode(
            bytes(private_key.public_key)
        ),
    }


def make_cybersource_response(status, info_codes=None, request_id="abc123"):
    """
    Build a stand-in for a CyberSource export compliance REST response

    Args:
        status (str): the decision, e.g. "COMPLETED"
        info_codes (list of str or None): sanctions list matches, if any
        request_id (str): the CyberSource request id

    Returns:
        SimpleNamespace: an object shaped like the SDK's response model
    """
    return SimpleNamespace(
        status=status,
        id=request_id,
        export_compliance_information=SimpleNamespace(info_codes=info_codes),
        to_dict=lambda: {
            "status": status,
            "id": request_id,
            "exportComplianceInformation": {"infoCodes": info_codes},
        },
    )
