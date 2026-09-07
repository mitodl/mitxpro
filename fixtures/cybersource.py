"""Fixtures for CyberSource tests"""

import pytest
from nacl.public import PrivateKey

from compliance.test_utils import (
    get_cybersource_test_settings,
    make_cybersource_response,
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


@pytest.fixture
def cybersource_mock_client(mocker, cybersource_settings):  # noqa: ARG001
    """Patch out the CyberSource REST client and return the mock"""
    mock_client = mocker.Mock()
    mocker.patch("compliance.api.get_cybersource_client", return_value=mock_client)
    return mock_client


@pytest.fixture
def cybersource_mock_client_responses(request, cybersource_mock_client):
    """Patch the REST client to return a given (status, info_codes) response"""
    status, info_codes = request.param
    cybersource_mock_client.validate_export_compliance.return_value = (
        make_cybersource_response(status, info_codes)
    )
    return cybersource_mock_client
