"""
Fixtures for hubspot_xpro tests
"""
from datetime import datetime
from types import SimpleNamespace

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from hubspot.crm.objects import SimplePublicObject
from mitol.hubspot_api.factories import HubspotObjectFactory

from b2b_ecommerce import factories as b2b_factories
from ecommerce import factories
from ecommerce.models import Order, Product
from users.models import User


# pylint: disable=redefined-outer-name

TIMESTAMPS = [
    datetime(2017, 1, 1, tzinfo=pytz.utc),
    datetime(2017, 1, 2, tzinfo=pytz.utc),
    datetime(2017, 1, 3, tzinfo=pytz.utc),
    datetime(2017, 1, 4, tzinfo=pytz.utc),
    datetime(2017, 1, 5, tzinfo=pytz.utc),
    datetime(2017, 1, 6, tzinfo=pytz.utc),
    datetime(2017, 1, 7, tzinfo=pytz.utc),
    datetime(2017, 1, 8, tzinfo=pytz.utc),
]

FAKE_OBJECT_ID = 1234
FAKE_HUBSPOT_ID = "1231213123"


@pytest.fixture
def mocked_celery(mocker):
    """Mock object that patches certain celery functions"""
    exception_class = TabError
    replace_mock = mocker.patch(
        "celery.app.task.Task.replace", autospec=True, side_effect=exception_class
    )
    group_mock = mocker.patch("celery.group", autospec=True)
    chain_mock = mocker.patch("celery.chain", autospec=True)

    yield SimpleNamespace(
        replace=replace_mock,
        group=group_mock,
        chain=chain_mock,
        replace_exception_class=exception_class,
    )


@pytest.fixture
def mock_logger(mocker):
    """Mock the logger"""
    yield mocker.patch("hubspot_xpro.tasks.log.error")


@pytest.fixture
def hubspot_order():
    """Return an order for testing with hubspot_xpro"""
    order = factories.OrderFactory()
    product_version = factories.ProductVersionFactory()
    factories.LineFactory(order=order, product_version=product_version)

    HubspotObjectFactory.create(
        content_object=order.purchaser,
        content_type=ContentType.objects.get_for_model(User),
        object_id=order.purchaser.id,
    )
    HubspotObjectFactory.create(
        content_object=product_version.product,
        content_type=ContentType.objects.get_for_model(Product),
        object_id=product_version.product.id,
    )

    return order


@pytest.fixture
def hubspot_order_id(hubspot_order):
    """Create a HubspotObject for hubspot_order"""
    return HubspotObjectFactory.create(
        content_object=hubspot_order,
        content_type=ContentType.objects.get_for_model(Order),
        object_id=hubspot_order.id,
    ).hubspot_id


@pytest.fixture
def hubspot_b2b_order():
    """Return an B2B order for testing with hubspot_xpro"""
    order = b2b_factories.B2BOrderFactory.create(status="created")
    coupon = b2b_factories.B2BCouponFactory.create(
        product=order.product_version.product
    )
    b2b_factories.B2BCouponRedemptionFactory.create(coupon=coupon, order=order)
    HubspotObjectFactory.create(
        content_object=order.product_version.product,
        content_type=ContentType.objects.get_for_model(Product),
        object_id=order.product_version.product.id,
    )
    return order


@pytest.fixture
def hubspot_b2b_order_id(hubspot_b2b_order):
    """Return a HubspotObject ID for hubspot_b2b_order"""
    return HubspotObjectFactory.create(
        content_object=hubspot_b2b_order,
        content_type=ContentType.objects.get_for_model(Order),
        object_id=hubspot_b2b_order.id,
    ).hubspot_id


@pytest.fixture
def mock_hubspot_api(mocker):
    """Mock the Hubspot CRM API"""
    mock_api = mocker.patch("mitol.hubspot_api.api.HubspotApi")
    mock_api.return_value.crm.objects.basic_api.create.return_value = (
        SimplePublicObject(id=FAKE_HUBSPOT_ID)
    )
    yield mock_api
