"""Testing utils around CyberSource"""
from nacl.public import PrivateKey
from nacl.encoding import Base64Encoder
from rest_framework import status

SERVICE_VERSION = "1.154"

DATA_DIR = "compliance/test_data/cybersource"


def get_cybersource_test_settings(private_key=None):
    """
    Generates a valid set of settings for CyberSource
    """
    if private_key is None:
        private_key = PrivateKey.generate()

    return {
        "CYBERSOURCE_WSDL_URL": (
            f"http://localhost/service/CyberSourceTransaction_{SERVICE_VERSION}.wsdl"
        ),
        "CYBERSOURCE_MERCHANT_ID": "merchant_id",
        "CYBERSOURCE_TRANSACTION_KEY": "transaction_key",
        "CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY": Base64Encoder.encode(
            bytes(private_key.public_key)
        ),
    }


def mock_cybersource_wsdl(mocked_responses, settings, service_version=SERVICE_VERSION):
    """
    Mocks the responses to achieve a functional WSDL
    """
    # in order for zeep to load the wsdl, it will load the wsdl and the accompanying xsd definitions
    with open(f"{DATA_DIR}/CyberSourceTransaction_{service_version}.wsdl", "r") as wsdl:
        mocked_responses.add(
            mocked_responses.GET,
            settings.CYBERSOURCE_WSDL_URL,
            body=wsdl.read(),
            status=status.HTTP_200_OK,
        )
    with open(f"{DATA_DIR}/CyberSourceTransaction_{SERVICE_VERSION}.xsd", "r") as xsd:
        mocked_responses.add(
            mocked_responses.GET,
            f"http://localhost/service/CyberSourceTransaction_{service_version}.xsd",
            body=xsd.read(),
            status=status.HTTP_200_OK,
        )


def mock_cybersource_wsdl_operation(mocked_responses, response_name):
    """
    Mock the response for an operation
    """
    with open(f"{DATA_DIR}/{response_name}.xml") as operation_response:
        mocked_responses.add(
            mocked_responses.POST,
            "http://localhost/service",
            body=operation_response.read(),
            status=status.HTTP_200_OK,
        )
