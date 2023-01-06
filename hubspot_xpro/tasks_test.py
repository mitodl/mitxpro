"""
Tests for hubspot_xpro tasks
"""
# pylint: disable=redefined-outer-name
from decimal import Decimal
from math import ceil

import pytest
from django.contrib.contenttypes.models import ContentType
from faker import Faker
from hubspot.crm.associations import BatchInputPublicAssociation, PublicAssociation
from hubspot.crm.objects import BatchInputSimplePublicObjectInput
from mitol.hubspot_api.api import HubspotAssociationType, HubspotObjectType
from mitol.hubspot_api.factories import HubspotObjectFactory, SimplePublicObjectFactory
from mitol.hubspot_api.models import HubspotObject

from b2b_ecommerce.factories import B2BOrderFactory
from b2b_ecommerce.models import B2BOrder
from ecommerce.factories import (
    LineFactory,
    OrderFactory,
    ProductFactory,
    ProductVersionFactory,
)
from ecommerce.models import Order, Product
from hubspot_xpro import tasks
from hubspot_xpro.api import make_contact_sync_message
from users.factories import UserFactory


pytestmark = [pytest.mark.django_db]

fake = Faker()


@pytest.mark.parametrize(
    "task_func",
    [
        "sync_contact_with_hubspot",
        "sync_product_with_hubspot",
        "sync_deal_with_hubspot",
        "sync_b2b_deal_with_hubspot",
    ],
)
def test_task_functions(mocker, task_func):
    """These task functions should call the api function of the same name and return a hubspot id"""
    mock_result = SimplePublicObjectFactory()
    mock_api_call = mocker.patch(
        f"hubspot_xpro.tasks.api.{task_func}", return_value=mock_result
    )
    mock_object_id = 101
    assert getattr(tasks, task_func)(mock_object_id) == mock_result.id
    mock_api_call.assert_called_once_with(mock_object_id)


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
    synced_products = ProductFactory.create_batch(103)
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
        list(
            zip(
                [contact.id for contact in contacts],
                [f"10001{i}" for i in range(id_count)],
            )
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


def test_batch_upsert_associations_chunked(settings, mocker):
    """
    batch_upsert_associations_chunked should make expected API calls
    """
    mock_hubspot_api = mocker.patch("hubspot_xpro.tasks.HubspotApi")
    orders = OrderFactory.create_batch(5)
    for order in orders:
        LineFactory.create(
            order=order,
            product_version=ProductVersionFactory.create(price=Decimal(200.00)),
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
