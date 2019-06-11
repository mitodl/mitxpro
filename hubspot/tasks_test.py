"""
Tests for hubspot tasks
"""
# pylint: disable=redefined-outer-name
from datetime import datetime
from unittest.mock import ANY

import pytest
import pytz

from faker import Faker

from ecommerce.factories import ProductFactory, LineFactory
from hubspot.api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
)
from hubspot.factories import HubspotErrorCheckFactory
from hubspot.models import HubspotErrorCheck
from hubspot.tasks import (
    sync_contact_with_hubspot,
    HUBSPOT_SYNC_URL,
    sync_product_with_hubspot,
    sync_deal_with_hubspot,
    sync_line_item_with_hubspot,
    check_hubspot_api_errors,
)
from users.factories import UserFactory

pytestmark = [pytest.mark.django_db]

fake = Faker()


@pytest.fixture
def mock_hubspot_request(mocker):
    """Mock the send hubspot request method"""
    yield mocker.patch("hubspot.tasks.send_hubspot_request", autospec=True)


def test_sync_contact_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a CONTACT sync"""
    user = UserFactory.create()
    sync_contact_with_hubspot(user.id)
    body = make_contact_sync_message(user.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_product_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a PRODUCT sync"""
    product = ProductFactory.create()
    sync_product_with_hubspot(product.id)
    body = make_product_sync_message(product.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "PRODUCT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_deal_with_hubspot(
    mocker, mock_hubspot_request, mocked_celery, hubspot_order
):
    """Test that send_hubspot_request is called properly for a DEAL sync"""
    sync_line_mock = mocker.patch(
        "hubspot.tasks.sync_line_item_with_hubspot", autospec=True
    )

    with pytest.raises(mocked_celery.replace_exception_class):
        sync_deal_with_hubspot.delay(hubspot_order.id)
    assert mocked_celery.group.call_count == 1

    body = make_deal_sync_message(hubspot_order.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "DEAL", HUBSPOT_SYNC_URL, "PUT", body=body
    )

    assert sync_line_mock.si.call_count == 1
    sync_line_mock.si.assert_any_call(hubspot_order.lines.first().id)

    assert mocked_celery.replace.call_count == 1
    assert mocked_celery.replace.call_args[0][1] == mocked_celery.chain.return_value


def test_sync_line_item_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a LINE_ITEM sync"""
    line = LineFactory.create()
    sync_line_item_with_hubspot(line.id)
    body = make_line_item_sync_message(line.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_errors_first_run(mock_hubspot_errors, mock_logger):
    """Test that HubspotErrorCheck is created on 1st run and nothing is logged"""
    assert HubspotErrorCheck.objects.count() == 0
    check_hubspot_api_errors()
    assert HubspotErrorCheck.objects.count() == 1
    assert mock_hubspot_errors.call_count == 1
    assert mock_logger.call_count == 0


@pytest.mark.parametrize(
    "last_check_dt,expected_errors,call_count",
    [
        [datetime(2015, 1, 1, tzinfo=pytz.utc), 4, 3],
        [datetime(2019, 5, 22, tzinfo=pytz.utc), 1, 1],
    ],
)
def test_sync_errors_new_errors(
    mock_hubspot_errors, mock_logger, last_check_dt, expected_errors, call_count
):
    """Test that errors more recent than last checked_on date are logged"""
    last_check = HubspotErrorCheckFactory.create(checked_on=last_check_dt)
    check_hubspot_api_errors()
    assert mock_hubspot_errors.call_count == call_count
    assert mock_logger.call_count == expected_errors
    assert HubspotErrorCheck.objects.first().checked_on > last_check.checked_on
