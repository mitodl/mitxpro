"""
Fixtures for hubspot tests
"""
from types import SimpleNamespace
import pytest
from ecommerce import factories

error_response_json = [
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": "16",
        "changeOccurredTimestamp": 1_558_727_887_000,
        "errorTimestamp": 1_558_727_887_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[16] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": "55",
        "changeOccurredTimestamp": 1_558_382_138_000,
        "errorTimestamp": 1_558_382_138_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[55] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": "116",
        "changeOccurredTimestamp": 1_558_727_887_000,
        "errorTimestamp": 1_508_727_887_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[116] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": "155",
        "changeOccurredTimestamp": 1_558_382_138_000,
        "errorTimestamp": 1_508_382_138_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[155] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
]


@pytest.fixture
def mock_hubspot_errors(mocker):
    """Mock the get_sync_errors API call, assuming a limit of 2"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors",
        side_effect=[error_response_json[0:2], error_response_json[2:]],
    )


@pytest.fixture()
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
