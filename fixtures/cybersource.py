"""Fxitures for CyberSource tests"""
# pylint: disable=redefined-outer-name

from nacl.public import PrivateKey
import pytest

from compliance.test_utils import (
    get_cybersource_test_settings,
    mock_cybersource_wsdl,
    mock_cybersource_wsdl_operation,
)


@pytest.fixture
def cybersource_private_key():
    """Creates a new NaCl private key"""
    return PrivateKey.generate()


@pytest.fixture
def cybersource_settings(settings, cybersource_private_key):
    """Configured CyberSource settings"""
    for attr_name, value in get_cybersource_test_settings(
        cybersource_private_key
    ).items():
        setattr(settings, attr_name, value)
    return settings


@pytest.fixture(params=[])
def cybersource_mock_client_responses(request, mocked_responses, cybersource_settings):
    """Mock out the components of a valid WSDL API"""
    mock_cybersource_wsdl(mocked_responses, cybersource_settings)
    mock_cybersource_wsdl_operation(mocked_responses, request.param)
    return mocked_responses
