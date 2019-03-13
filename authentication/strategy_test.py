"""Tests for the strategy"""
from django.http import HttpRequest
from rest_framework.request import Request

from authentication.utils import load_drf_strategy


def test_strategy_init(mocker):
    """Test that the constructor works as expected"""
    drf_request = mocker.Mock()
    strategy = load_drf_strategy(request=drf_request)
    assert strategy.drf_request == drf_request
    assert strategy.request == drf_request._request  # pylint: disable=protected-access


def test_strategy_request_data(mocker):
    """Tests that the strategy request_data correctly returns the DRF request data"""
    drf_request = mocker.Mock()
    strategy = load_drf_strategy(request=drf_request)
    assert strategy.request_data() == drf_request.data


def test_strategy_clean_authenticate_args(mocker):
    """Tests that the strategy clean_authenticate_args moves the request to kwargs"""
    # NOTE: don't pass this to load_drf_Strategy, it will error
    drf_request = Request(mocker.Mock(spec=HttpRequest))
    strategy = load_drf_strategy(mocker.Mock())
    assert strategy.clean_authenticate_args(drf_request, 2, 3, kwarg1=1, kwarg2=2) == (
        (2, 3),
        {"request": drf_request, "kwarg1": 1, "kwarg2": 2},
    )
