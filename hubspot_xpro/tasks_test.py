"""
Tests for hubspot_xpro tasks
"""

from decimal import Decimal
from math import ceil

import pytest
from django.contrib.contenttypes.models import ContentType
from faker import Faker
from hubspot.crm.associations import BatchInputPublicAssociation, PublicAssociation
from hubspot.crm.objects import ApiException, BatchInputSimplePublicObjectInput
from mitol.hubspot_api.api import HubspotAssociationType, HubspotObjectType
from mitol.hubspot_api.exceptions import TooManyRequestsException
from mitol.hubspot_api.factories import HubspotObjectFactory, SimplePublicObjectFactory
from mitol.hubspot_api.models import HubspotObject

from b2b_ecommerce.factories import B2BOrderFactory
from b2b_ecommerce.models import B2BOrder
from courses.factories import CourseFactory
from ecommerce.factories import (
    LineFactory,
    OrderFactory,
    ProductFactory,
    ProductVersionFactory,
)
from ecommerce.models import Order, Product
from hubspot_xpro import tasks
from hubspot_xpro.api import make_contact_sync_message
from hubspot_xpro.tasks import task_obj_lock
from users.factories import UserFactory

pytestmark = [pytest.mark.django_db]

fake = Faker()


SYNC_FUNCTIONS = [
    "sync_contact_with_hubspot",
    "sync_product_with_hubspot",
    "sync_deal_with_hubspot",
]


@pytest.mark.parametrize("task_func", SYNC_FUNCTIONS)
def test_task_functions(mocker, task_func):
    """These task functions should call the api function of the same name and return a hubspot id"""
    mock_result = SimplePublicObjectFactory()
    mock_api_call = mocker.patch(
        f"hubspot_xpro.tasks.api.{task_func}", return_value=mock_result
    )
    mock_object_id = 101
    assert getattr(tasks, task_func)(mock_object_id) == mock_result.id
    mock_api_call.assert_called_once_with(mock_object_id)


@pytest.mark.parametrize("task_func", SYNC_FUNCTIONS)
@pytest.mark.parametrize(
    "status, expected_error",  # noqa: PT006
    [[429, TooManyRequestsException], [500, ApiException]],  # noqa: PT007
)
def test_task_functions_error(mocker, task_func, status, expected_error):
    """These task functions should return the expected exception class"""
    mocker.patch(
        f"hubspot_xpro.tasks.api.{task_func}", side_effect=expected_error(status=status)
    )
    with pytest.raises(expected_error):
        getattr(tasks, task_func)(101)


@pytest.mark.parametrize("create", [True, False])
@pytest.mark.parametrize("max_batches", [5, 10])
def test_batch_upsert_hubspot_deals(
    settings, mocker, mocked_celery, create, max_batches
):
    """batch_upsert_hubspot_deals should make expected calls"""
    settings.HUBSPOT_MAX_CONCURRENT_TASKS = max_batches
    unsynced_deals = OrderFactory.create_batch(103)
    synced_deals = OrderFactory.create_batch(201)
    content_type = ContentType.objects.get_for_model(Order)
    for deal in synced_deals:
        HubspotObjectFactory.create(
            content_type=content_type, object_id=deal.id, content_object=deal
        )
    mock_api_call = mocker.patch(
        "hubspot_xpro.tasks.batch_upsert_hubspot_deals_chunked"
    )
    with pytest.raises(TabError):
        tasks.batch_upsert_hubspot_deals.delay(create)
    mocked_celery.replace.assert_called_once()
    expected_deal_ids = sorted(
        [deal.id for deal in (unsynced_deals if create else synced_deals)]
    )
    expected_batch_size = ceil(len(expected_deal_ids) / max_batches)
    mock_api_call.s.assert_any_call(expected_deal_ids[0:expected_batch_size])
    mock_api_call.s.assert_any_call(
        expected_deal_ids[expected_batch_size : expected_batch_size * 2]
    )
    assert mock_api_call.s.call_count == max_batches


def test_batch_upsert_hubspot_deals_chunked(mocker):
    """batch_upsert_hubspot_deals_chunked should make expected calls"""
    orders = OrderFactory.create_batch(3)
    mock_results = SimplePublicObjectFactory.create_batch(3)
    mock_sync_deal = mocker.patch(
        "hubspot_xpro.tasks.api.sync_deal_with_hubspot", side_effect=mock_results
    )
    result = tasks.batch_upsert_hubspot_deals_chunked([order.id for order in orders])
    assert mock_sync_deal.call_count == 3
    assert result == [result.id for result in mock_results]


@pytest.mark.parametrize("create", [True, False])
@pytest.mark.parametrize("max_batches", [20, 1])
def test_batch_upsert_b2b_hubspot_deals(
    settings, mocker, mocked_celery, create, max_batches
):
    """batch_upsert_hubspot_b2b_deals should make expected calls"""
    settings.HUBSPOT_MAX_CONCURRENT_TASKS = max_batches
    unsynced_deals = B2BOrderFactory.create_batch(2)
    synced_deals = B2BOrderFactory.create_batch(3)
    content_type = ContentType.objects.get_for_model(B2BOrder)
    for deal in synced_deals:
        HubspotObjectFactory.create(
            content_type=content_type, object_id=deal.id, content_object=deal
        )
    mock_api_call = mocker.patch(
        "hubspot_xpro.tasks.batch_upsert_hubspot_b2b_deals_chunked"
    )
    with pytest.raises(TabError):
        tasks.batch_upsert_hubspot_b2b_deals.delay(create)
    mocked_celery.replace.assert_called_once()
    expected_deals = sorted(
        [deal.id for deal in (unsynced_deals if create else synced_deals)]
    )
    expected_batch_size = ceil(len(expected_deals) / max_batches)
    mock_api_call.s.assert_any_call(expected_deals[0:expected_batch_size])
    assert mock_api_call.s.call_count == min(max_batches, len(expected_deals))


def test_batch_upsert_hubspot_b2b_deals_chunked(mocker):
    """batch_upsert_hubspot_b2b_deals_chunked should make expected calls"""
    orders = B2BOrderFactory.create_batch(3)
    mock_results = SimplePublicObjectFactory.create_batch(3)
    mock_sync_deal = mocker.patch(
        "hubspot_xpro.tasks.api.sync_b2b_deal_with_hubspot", side_effect=mock_results
    )
    result = tasks.batch_upsert_hubspot_b2b_deals_chunked(
        [order.id for order in orders]
    )
    assert mock_sync_deal.call_count == 3
    assert result == [result.id for result in mock_results]


@pytest.mark.parametrize("create", [True, False])
def test_batch_upsert_hubspot_objects(settings, mocker, mocked_celery, create):
    """batch_upsert_hubspot_objects should call batch_upsert_hubspot_objects_chunked w/correct args"""
    settings.HUBSPOT_MAX_CONCURRENT_TASKS = 5
    mock_create = mocker.patch(
        "hubspot_xpro.tasks.batch_create_hubspot_objects_chunked.s"
    )
    mock_update = mocker.patch(
        "hubspot_xpro.tasks.batch_update_hubspot_objects_chunked.s"
    )
    unsynced_products = ProductFactory.create_batch(2)
    course = CourseFactory.create()
    synced_products = ProductFactory.create_batch(103, content_object__course=course)
    content_type = ContentType.objects.get_for_model(Product)
    hs_objects = [
        HubspotObjectFactory.create(
            content_type=content_type, object_id=product.id, content_object=product
        )
        for product in synced_products
    ]
    with pytest.raises(TabError):
        tasks.batch_upsert_hubspot_objects.delay(
            HubspotObjectType.PRODUCTS.value, "product", "ecommerce", create=create
        )
    mocked_celery.replace.assert_called_once()
    if create:
        assert mock_create.call_count == 2
        mock_create.assert_any_call(
            HubspotObjectType.PRODUCTS.value, "product", [unsynced_products[0].id]
        )
        mock_create.assert_any_call(
            HubspotObjectType.PRODUCTS.value, "product", [unsynced_products[1].id]
        )
        mock_update.assert_not_called()
    else:
        assert mock_update.call_count == 5
        mock_update.assert_any_call(
            HubspotObjectType.PRODUCTS.value,
            "product",
            [
                (hso.object_id, hso.hubspot_id)
                for hso in sorted(hs_objects, key=lambda o: o.object_id)[
                    0:21
                ]  # 103/5 == 21
            ],
        )
        mock_create.assert_not_called()


@pytest.mark.parametrize("id_count", [5, 15])
def test_batch_update_hubspot_objects_chunked(mocker, id_count):
    """batch_update_hubspot_objects_chunked should make expected api calls and args"""
    contacts = UserFactory.create_batch(id_count)
    mock_ids = sorted(
        zip(
            [contact.id for contact in contacts],
            [f"10001{i}" for i in range(id_count)],
        )
    )
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    mock_hubspot_api.return_value.crm.objects.batch_api.update.return_value = (
        mocker.Mock(
            results=[SimplePublicObjectFactory(id=mock_id[1]) for mock_id in mock_ids]
        )
    )
    expected_batches = 1 if id_count == 5 else 2
    tasks.batch_update_hubspot_objects_chunked(
        HubspotObjectType.CONTACTS.value, "user", mock_ids
    )
    assert (
        mock_hubspot_api.return_value.crm.objects.batch_api.update.call_count
        == expected_batches
    )
    mock_hubspot_api.return_value.crm.objects.batch_api.update.assert_any_call(
        HubspotObjectType.CONTACTS.value,
        BatchInputSimplePublicObjectInput(
            inputs=[
                {
                    "id": mock_id[1],
                    "properties": make_contact_sync_message(mock_id[0]).properties,
                }
                for mock_id in mock_ids[0 : min(id_count, 10)]
            ]
        ),
    )


@pytest.mark.parametrize(
    "status, expected_error",  # noqa: PT006
    [[429, TooManyRequestsException], [500, ApiException]],  # noqa: PT007
)
def test_batch_update_hubspot_objects_chunked_error(mocker, status, expected_error):
    """batch_update_hubspot_objects_chunked raise expected exception"""
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    mock_hubspot_api.return_value.crm.objects.batch_api.update.side_effect = (
        ApiException(status=status)
    )
    mock_sync_contacts = mocker.patch(
        "hubspot_xpro.tasks.api.sync_contact_with_hubspot",
        side_effect=(ApiException(status=status)),
    )
    chunk = [(user.id, "123") for user in UserFactory.create_batch(3)]
    with pytest.raises(expected_error):
        tasks.batch_update_hubspot_objects_chunked(
            HubspotObjectType.CONTACTS.value,
            "user",
            chunk,
        )
    for item in chunk:
        mock_sync_contacts.assert_any_call(item[0])


@pytest.mark.parametrize("id_count", [5, 15])
def test_batch_create_hubspot_objects_chunked(mocker, id_count):
    """batch_create_hubspot_objects_chunked should make expected api calls and args"""
    contacts = UserFactory.create_batch(id_count)
    mock_ids = sorted([contact.id for contact in contacts])
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    mock_hubspot_api.return_value.crm.objects.batch_api.update.return_value = (
        mocker.Mock(
            results=[SimplePublicObjectFactory(id=mock_id) for mock_id in mock_ids]
        )
    )
    expected_batches = 1 if id_count == 5 else 2
    tasks.batch_create_hubspot_objects_chunked(
        HubspotObjectType.CONTACTS.value, "user", mock_ids
    )
    assert (
        mock_hubspot_api.return_value.crm.objects.batch_api.create.call_count
        == expected_batches
    )
    mock_hubspot_api.return_value.crm.objects.batch_api.create.assert_any_call(
        HubspotObjectType.CONTACTS.value,
        BatchInputSimplePublicObjectInput(
            inputs=[
                make_contact_sync_message(mock_id)
                for mock_id in mock_ids[0 : min(id_count, 10)]
            ]
        ),
    )


@pytest.mark.parametrize(
    "status, expected_error",  # noqa: PT006
    [[429, TooManyRequestsException], [500, ApiException]],  # noqa: PT007
)
def test_batch_create_hubspot_objects_chunked_error(mocker, status, expected_error):
    """batch_create_hubspot_objects_chunked raise expected exception"""
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    mock_hubspot_api.return_value.crm.objects.batch_api.create.side_effect = (
        ApiException(status=status)
    )
    mock_sync_contact = mocker.patch(
        "hubspot_xpro.tasks.api.sync_contact_with_hubspot",
        side_effect=(ApiException(status=status)),
    )
    chunk = sorted([user.id for user in UserFactory.create_batch(3)])
    with pytest.raises(expected_error):
        tasks.batch_create_hubspot_objects_chunked(
            HubspotObjectType.CONTACTS.value,
            "user",
            chunk,
        )
    for item in chunk:
        mock_sync_contact.assert_any_call(item)


def test_batch_upsert_associations(settings, mocker, mocked_celery):
    """
    batch_upsert_associations should call batch_upsert_associations_chunked w/correct lists of ids
    """
    mock_assoc_chunked = mocker.patch(
        "hubspot_xpro.tasks.batch_upsert_associations_chunked"
    )
    settings.HUBSPOT_MAX_CONCURRENT_TASKS = 4
    order_ids = sorted([app.id for app in OrderFactory.create_batch(10)])
    with pytest.raises(TabError):
        tasks.batch_upsert_associations.delay()
    mock_assoc_chunked.s.assert_any_call(order_ids[0:3])
    mock_assoc_chunked.s.assert_any_call(order_ids[6:9])
    mock_assoc_chunked.s.assert_any_call([order_ids[9]])
    assert mock_assoc_chunked.s.call_count == 4

    with pytest.raises(TabError):
        tasks.batch_upsert_associations.delay(order_ids[3:5])
    mock_assoc_chunked.s.assert_any_call([order_ids[3]])
    mock_assoc_chunked.s.assert_any_call([order_ids[4]])


def test_batch_upsert_associations_chunked(mocker):
    """
    batch_upsert_associations_chunked should make expected API calls
    """
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    orders = OrderFactory.create_batch(5)
    for order in orders:
        LineFactory.create(
            order=order,
            product_version=ProductVersionFactory.create(price=Decimal("200.00")),
        )
    expected_line_associations = [
        PublicAssociation(
            _from=HubspotObjectFactory.create(
                content_type=ContentType.objects.get_for_model(order.lines.first()),
                object_id=order.lines.first().id,
                content_object=order.lines.first(),
            ).hubspot_id,
            to=HubspotObjectFactory.create(
                content_type=ContentType.objects.get_for_model(order),
                object_id=order.id,
                content_object=order,
            ).hubspot_id,
            type=HubspotAssociationType.LINE_DEAL.value,
        )
        for order in orders
    ]
    expected_contact_associations = [
        PublicAssociation(
            _from=HubspotObject.objects.get(
                content_type=ContentType.objects.get_for_model(order),
                object_id=order.id,
            ).hubspot_id,
            to=HubspotObjectFactory.create(
                content_type=ContentType.objects.get_for_model(order.purchaser),
                object_id=order.purchaser.id,
                content_object=order.purchaser,
            ).hubspot_id,
            type=HubspotAssociationType.DEAL_CONTACT.value,
        )
        for order in orders
    ]
    tasks.batch_upsert_associations_chunked.delay([order.id for order in orders])
    mock_hubspot_api.return_value.crm.associations.batch_api.create.assert_any_call(
        HubspotObjectType.LINES.value,
        HubspotObjectType.DEALS.value,
        batch_input_public_association=BatchInputPublicAssociation(
            inputs=expected_line_associations
        ),
    )
    mock_hubspot_api.return_value.crm.associations.batch_api.create.assert_any_call(
        HubspotObjectType.DEALS.value,
        HubspotObjectType.CONTACTS.value,
        batch_input_public_association=BatchInputPublicAssociation(
            inputs=expected_contact_associations
        ),
    )


@pytest.mark.parametrize(
    "func_name,args,kwargs,result",  # noqa: PT006
    [
        ["func1", [2345], None, "func1_2345"],  # noqa: PT007
        ["func2", None, {"order_id": 5678}, "func2_5678"],  # noqa: PT007
        ["func2a", [], {"user_id": 5678}, "func2a_5678"],  # noqa: PT007
        ["func3", None, None, "func3"],  # noqa: PT007
        ["func3a", None, {}, "func3a"],  # noqa: PT007
    ],
)
def test_task_obj_lock(func_name, args, kwargs, result):
    """task_obj_lock should return expected result string"""
    assert task_obj_lock(func_name, args, kwargs) == result


def test_sync_failed_contacts(mocker):
    """sync_failed_contacts should try to sync each contact and return a list of failed contact ids"""
    user_ids = sorted(user.id for user in UserFactory.create_batch(4))
    mock_sync = mocker.patch(
        "hubspot_xpro.tasks.api.sync_contact_with_hubspot",
        side_effect=[
            mocker.Mock(),
            ApiException(status=500, reason="err"),
            mocker.Mock(),
            ApiException(status=429, reason="tmr"),
        ],
    )
    result = tasks.sync_failed_contacts(user_ids)
    assert mock_sync.call_count == 4
    assert result == [user_ids[1], user_ids[3]]


@pytest.mark.parametrize("for_contacts", [True, False])
@pytest.mark.parametrize("has_errors", [True, False])
def test_handle_failed_batch_chunk(mocker, for_contacts, has_errors):
    """handle_failed_batch_chunk should retry contacts only and log exceptions as appropriate"""
    object_ids = [1, 2, 3, 4]
    expected_sync_result = object_ids if has_errors or not for_contacts else []
    hubspot_type = (
        HubspotObjectType.CONTACTS.value
        if for_contacts
        else HubspotObjectType.DEALS.value
    )
    mock_sync_contacts = mocker.patch(
        "hubspot_xpro.tasks.sync_failed_contacts", return_value=expected_sync_result
    )
    mock_log = mocker.patch("hubspot_xpro.tasks.log.exception")
    tasks.handle_failed_batch_chunk(object_ids, hubspot_type)
    assert mock_sync_contacts.call_count == (
        1 if hubspot_type == HubspotObjectType.CONTACTS.value else 0
    )
    if has_errors or not for_contacts:
        mock_log.assert_called_once_with(
            "Exception when batch syncing Hubspot ids %s of type %s",
            f"{expected_sync_result}",
            hubspot_type,
        )
