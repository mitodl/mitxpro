"""Tests for the strategy"""

import pytest
from django.http import HttpRequest, QueryDict
from rest_framework.request import Request

from authentication.utils import load_drf_strategy


def test_strategy_init(mocker):
    """Test that the constructor works as expected"""
    drf_request = mocker.Mock()
    strategy = load_drf_strategy(request=drf_request)
    assert strategy.drf_request == drf_request
    assert strategy.request == drf_request._request  # noqa: SLF001


@pytest.mark.parametrize(
    "data",
    [
        {"email": "a@example.com", "partial_token": "tok"},
        QueryDict("email=a%40example.com&partial_token=tok"),
    ],
)
def test_strategy_request_data(mocker, data):
    """request_data returns the DRF request data as a plain dict of scalar values"""
    drf_request = mocker.Mock(data=data)
    strategy = load_drf_strategy(request=drf_request)
    assert strategy.request_data() == {"email": "a@example.com", "partial_token": "tok"}


def test_strategy_request_data_with_confirmation(mocker):
    """Confirming an external resume adds the confirmation fields without turning values into lists"""
    drf_request = mocker.Mock(
        data=QueryDict("partial_token=tok&verification_code=code")
    )
    strategy = load_drf_strategy(request=drf_request)
    strategy.confirm_external_resume("nonce")
    assert strategy.request_data() == {
        "partial_token": "tok",
        "verification_code": "code",
        "partial_pipeline_confirm": "1",
        "partial_pipeline_confirm_nonce": "nonce",
    }


@pytest.mark.parametrize(
    "value",
    [
        {"email": "a@example.com", "password": "secret"},
        QueryDict("email=a%40example.com&password=secret"),
    ],
)
def test_strategy_to_session_value_strips_password(mocker, value):
    """Values persisted into partials and the session never include the password"""
    strategy = load_drf_strategy(request=mocker.Mock())
    assert strategy.to_session_value(value) == {"email": "a@example.com"}


def test_strategy_clean_authenticate_args(mocker):
    """Tests that the strategy clean_authenticate_args drops the positional request"""
    # NOTE: don't pass this to load_drf_Strategy, it will error
    drf_request = Request(mocker.Mock(spec=HttpRequest))
    strategy = load_drf_strategy(mocker.Mock())
    assert strategy.clean_authenticate_args(drf_request, 2, 3, kwarg1=1, kwarg2=2) == (
        (2, 3),
        {"kwarg1": 1, "kwarg2": 2},
    )
