"""
Tests for hubspot tasks
"""
# pylint: disable=redefined-outer-name
from unittest.mock import ANY

import pytest

from faker import Faker

from ecommerce.factories import ProductFactory, LineFactory, OrderFactory
from hubspot.api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
    make_b2b_deal_sync_message,
    make_b2b_product_sync_message,
)
from hubspot.conftest import TIMESTAMPS, FAKE_OBJECT_ID
from hubspot.factories import HubspotErrorCheckFactory, HubspotLineResyncFactory
from hubspot.models import HubspotErrorCheck, HubspotLineResync
from hubspot.tasks import (
    sync_contact_with_hubspot,
    HUBSPOT_SYNC_URL,
    sync_product_with_hubspot,
    sync_deal_with_hubspot,
    sync_line_item_with_hubspot,
    sync_b2b_deal_with_hubspot,
    sync_b2b_product_with_hubspot,
    check_hubspot_api_errors,
    retry_invalid_line_associations,
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
    mock_sync_line, mock_hubspot_request, mocked_celery, hubspot_order
):
    """Test that send_hubspot_request is called properly for a DEAL sync"""
    with pytest.raises(mocked_celery.replace_exception_class):
        sync_deal_with_hubspot.delay(hubspot_order.id)
    assert mocked_celery.group.call_count == 1

    body = make_deal_sync_message(hubspot_order.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "DEAL", HUBSPOT_SYNC_URL, "PUT", body=body
    )

    assert mock_sync_line.si.call_count == 1
    mock_sync_line.si.assert_any_call(hubspot_order.lines.first().id)

    assert mocked_celery.replace.call_count == 1
    assert mocked_celery.replace.call_args[0][1] == mocked_celery.chain.return_value


def test_b2b_sync_deal_with_hubspot(
    mock_hubspot_request, mocked_celery, hubspot_b2b_order
):
    """Test that send_hubspot_request is called properly for a DEAL sync"""
    with pytest.raises(mocked_celery.replace_exception_class):
        sync_b2b_deal_with_hubspot.delay(hubspot_b2b_order.id)
    assert mocked_celery.group.call_count == 1

    body = make_b2b_deal_sync_message(hubspot_b2b_order.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "DEAL", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_b2b_product_with_hubspot(mock_hubspot_request, hubspot_b2b_order):
    """Test that send_hubspot_request is called properly for a LINE_ITEM sync"""
    sync_b2b_product_with_hubspot(hubspot_b2b_order.id)
    body = make_b2b_product_sync_message(hubspot_b2b_order.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_line_item_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a LINE_ITEM sync"""
    line = LineFactory.create()
    sync_line_item_with_hubspot(line.id)
    body = make_line_item_sync_message(line.id)
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_errors_first_run(settings, mock_hubspot_errors, mock_logger):
    """Test that HubspotErrorCheck is created on 1st run and nothing is logged"""
    settings.HUBSPOT_API_KEY = "dkfjKJ2jfd"
    assert HubspotErrorCheck.objects.count() == 0
    check_hubspot_api_errors()
    assert HubspotErrorCheck.objects.count() == 1
    assert mock_hubspot_errors.call_count == 1
    assert mock_logger.call_count == 0


@pytest.mark.parametrize(
    "last_check_dt,expected_errors,call_count",
    [[TIMESTAMPS[0], 4, 3], [TIMESTAMPS[6], 1, 1]],
)
def test_sync_errors_new_errors(
    settings,
    mock_hubspot_errors,
    mock_logger,
    last_check_dt,
    expected_errors,
    call_count,
):  # pylint: disable=too-many-arguments
    """Test that errors more recent than last checked_on date are logged"""
    settings.HUBSPOT_API_KEY = "dkfjKJ2jfd"
    last_check = HubspotErrorCheckFactory.create(checked_on=last_check_dt)
    check_hubspot_api_errors()
    assert mock_hubspot_errors.call_count == call_count
    assert mock_logger.call_count == expected_errors
    assert HubspotErrorCheck.objects.first().checked_on > last_check.checked_on


@pytest.mark.parametrize("model_that_exists", ["LINE_ITEM", "DEAL"])
def test_retry_invalid_line_associations(
    settings, mocker, mock_sync_line, model_that_exists
):
    """Test that line's are resynced if associated deals exists in hubspot"""
    mock_exists_in_hubspot = mocker.patch(
        "hubspot.tasks.exists_in_hubspot",
        side_effect=(lambda object_type, _: object_type == model_that_exists),
    )
    HubspotLineResyncFactory.create_batch(3)
    assert HubspotLineResync.objects.count() == 3

    settings.HUBSPOT_API_KEY = "dkfjKJ2jfd"
    retry_invalid_line_associations()
    if model_that_exists == "LINE_ITEM":
        assert mock_exists_in_hubspot.call_count == 3
        assert HubspotLineResync.objects.count() == 0
    else:
        assert mock_exists_in_hubspot.call_count == 6
        assert mock_sync_line.call_count == 3


def test_create_hubspot_line_resync(
    settings, mock_hubspot_line_error, mock_retry_lines
):
    """Test that lines are re-synced if the error is INVALID_ASSOCIATION_PROPERTY and the order has since been synced"""
    HubspotErrorCheckFactory.create(checked_on=TIMESTAMPS[0])
    order = OrderFactory(id=FAKE_OBJECT_ID)
    line = LineFactory(order=order, id=FAKE_OBJECT_ID)

    settings.HUBSPOT_API_KEY = "dkfjKJ2jfd"
    check_hubspot_api_errors()
    assert mock_hubspot_line_error.call_count == 2
    assert mock_retry_lines.call_count == 1
    assert HubspotLineResync.objects.count() == 1
    assert HubspotLineResync.objects.first().line == line


def test_ignore_hubspot_b2b_line_error(
    settings, mock_hubspot_b2b_line_error, mock_logger
):
    """Test that a b2b line error is ignored"""
    HubspotErrorCheckFactory.create(checked_on=TIMESTAMPS[0])
    settings.HUBSPOT_API_KEY = "dkfjKJ2jfd"
    check_hubspot_api_errors()
    assert mock_hubspot_b2b_line_error.call_count == 2
    assert HubspotLineResync.objects.count() == 0
    mock_logger.assert_not_called()


def test_skip_error_checks(settings, mock_hubspot_errors):
    """Test that no requests to Hubspot are made if the HUBSPOT_API_KEY is not set """
    settings.HUBSPOT_API_KEY = None
    check_hubspot_api_errors()
    assert mock_hubspot_errors.call_count == 0
