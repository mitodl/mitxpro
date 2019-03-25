"""
Tests for ecommerce permissions
"""
from ecommerce.api import generate_cybersource_sa_signature
from ecommerce.permissions import IsSignedByCyberSource


def test_has_signature(settings, mocker):
    """
    If the payload has a valid signature, it should pass the permissions test
    """
    settings.CYBERSOURCE_SECURITY_KEY = "fake"

    payload = {"a": "b", "c": "d", "e": "f"}
    keys = sorted(payload.keys())
    payload["signed_field_names"] = ",".join(keys)
    payload["signature"] = generate_cybersource_sa_signature(payload)

    request = mocker.MagicMock(data=payload)
    assert IsSignedByCyberSource().has_permission(request, mocker.MagicMock()) is True


def test_has_wrong_signature(settings, mocker):
    """
    If the payload has an invalid signature, it should fail the permissions test
    """
    settings.CYBERSOURCE_SECURITY_KEY = "fake"

    payload = {"a": "b", "c": "d", "e": "f"}
    keys = sorted(payload.keys())
    payload["signed_field_names"] = ",".join(keys)
    payload["signature"] = "signed"

    request = mocker.MagicMock(data=payload)
    assert IsSignedByCyberSource().has_permission(request, mocker.MagicMock()) is False
