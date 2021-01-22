"""
Fixtures for hubspot tests
"""
from datetime import datetime
from types import SimpleNamespace

import pytz
from django.conf import settings
import pytest
from b2b_ecommerce import factories as b2b_factories
from b2b_ecommerce.models import B2B_INTEGRATION_PREFIX
from ecommerce import factories
from hubspot.api import hubspot_timestamp

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


error_response_json = [
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-16",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[7]),
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[16] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-55",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[5]),
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[55] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-116",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[4]),
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[116] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-155",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[3]),
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[155] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
]

line_error_response_json = [
    {
        "portalId": 5_890_463,
        "objectType": "LINE_ITEM",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-{FAKE_OBJECT_ID}",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[2]),
        "type": "INVALID_ASSOCIATION_PROPERTY",
        "details": f"Invalid associations [hs_assoc__deal_id: {settings.HUBSPOT_ID_PREFIX}-{FAKE_OBJECT_ID}]. Do those objects exist?",
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "LINE_ITEM",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-{B2B_INTEGRATION_PREFIX}{FAKE_OBJECT_ID + 1}",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[2]),
        "type": "INVALID_ASSOCIATION_PROPERTY",
        "details": f"Invalid associations [hs_assoc__deal_id: {settings.HUBSPOT_ID_PREFIX}-{B2B_INTEGRATION_PREFIX}{FAKE_OBJECT_ID}]. Do those objects exist?",
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "LINE_ITEM",
        "integratorObjectId": f"{settings.HUBSPOT_ID_PREFIX}-{FAKE_OBJECT_ID + 2}",
        "changeOccurredTimestamp": hubspot_timestamp(TIMESTAMPS[0]),
        "errorTimestamp": hubspot_timestamp(TIMESTAMPS[2]),
        "type": "INVALID_ASSOCIATION_PROPERTY",
        "details": f"Invalid associations [hs_assoc__deal_id: {settings.HUBSPOT_ID_PREFIX}-{FAKE_OBJECT_ID}]. Do those objects exist?",
        "status": "OPEN",
    },
]


@pytest.fixture
def mock_hubspot_errors(mocker):
    """Mock the get_sync_errors API call, assuming a limit of 2"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors",
        side_effect=[error_response_json[0:2], error_response_json[2:], []],
    )


@pytest.fixture
def mock_hubspot_line_error(mocker):
    """Mock the get_sync_errors API call and return a line sync error with an invalid association property"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors", side_effect=[line_error_response_json[0:1], []]
    )


@pytest.fixture
def mock_hubspot_line_errors(mocker):
    """Mock the get_sync_errors API call and return multiple line sync error with invalid association properties"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors", side_effect=[line_error_response_json]
    )


@pytest.fixture
def mock_hubspot_b2b_line_error(mocker):
    """Mock the get_sync_errors API call and return a b2b line sync error with invalid association properties"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors", side_effect=[[line_error_response_json[1]], []]
    )


@pytest.fixture
def mock_retry_lines(mocker):
    """Mock the retry_invalid_line_associations function"""
    yield mocker.patch("hubspot.tasks.retry_invalid_line_associations")


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
    """ Mock the logger """
    yield mocker.patch("hubspot.tasks.log.error")


@pytest.fixture
def mock_hubspot_request(mocker):
    """Mock the send hubspot request method"""
    yield mocker.patch("hubspot.tasks.send_hubspot_request")


@pytest.fixture
def mock_hubspot_api_request(mocker):
    """Mock the send hubspot request method"""
    yield mocker.patch("hubspot.api.send_hubspot_request")


@pytest.fixture
def hubspot_order():
    """ Return an order for testing with hubspot"""
    order = factories.OrderFactory()
    product_version = factories.ProductVersionFactory()
    company = factories.CompanyFactory()
    payment_version = factories.CouponPaymentVersionFactory(company=company)
    coupon_version = factories.CouponVersionFactory(payment_version=payment_version)
    factories.LineFactory(order=order, product_version=product_version)
    factories.CouponRedemptionFactory(order=order, coupon_version=coupon_version)
    return order


@pytest.fixture
def hubspot_b2b_order():
    """ Return an B2B order for testing with hubspot"""
    order = b2b_factories.B2BOrderFactory.create(status="created")
    coupon = b2b_factories.B2BCouponFactory.create(
        product=order.product_version.product
    )
    b2b_factories.B2BCouponRedemptionFactory.create(coupon=coupon, order=order)
    return order


@pytest.fixture
def mock_sync_line(mocker):
    """ Mock calls to sync_line_item_with_hubspot """
    yield mocker.patch("hubspot.tasks.sync_line_item_with_hubspot", autospec=True)
