"""Tests for hubspot_xpro.api"""
import pytest
from django.contrib.contenttypes.models import ContentType
from mitol.hubspot_api.factories import HubspotObjectFactory, SimplePublicObjectFactory
from mitol.hubspot_api.models import HubspotObject

from b2b_ecommerce.models import B2BLine
from ecommerce.factories import LineFactory, ProductFactory, ProductVersionFactory
from ecommerce.models import Product
from hubspot_xpro import api
from hubspot_xpro.conftest import FAKE_HUBSPOT_ID
from hubspot_xpro.serializers import (
    B2BOrderToDealSerializer,
    B2BOrderToLineItemSerializer,
    LineSerializer,
    OrderToDealSerializer,
    ProductSerializer,
)
from users.factories import UserFactory


pytestmark = [pytest.mark.django_db]


@pytest.mark.django_db
def test_make_contact_sync_message(user):
    """Test make_contact_sync_message serializes a user and returns a properly formatted sync message"""
    contact_sync_message = api.make_contact_sync_message(user.id)
    assert contact_sync_message.properties == {
        "address": "\n".join(user.legal_address.street_address),
        "birth_year": int(user.profile.birth_year),
        "city": user.legal_address.city,
        "company": user.profile.company,
        "company_size": user.profile.company_size or "",
        "country": user.legal_address.country,
        "email": user.email,
        "firstname": user.legal_address.first_name,
        "gender": user.profile.gender,
        "highest_education": user.profile.highest_education,
        "industry": user.profile.industry,
        "job_function": user.profile.job_function,
        "jobtitle": user.profile.job_title,
        "lastname": user.legal_address.last_name,
        "leadership_level": user.profile.leadership_level,
        "name": user.name,
        "state": user.legal_address.state_or_territory,
        "zip": user.legal_address.postal_code,
    }


@pytest.mark.django_db
def test_make_deal_sync_message(hubspot_order):
    """Test make_deal_sync_message serializes an order and returns a properly formatted sync message"""
    deal_sync_message = api.make_deal_sync_message(hubspot_order.id)
    serialized_order = OrderToDealSerializer(hubspot_order).data

    assert deal_sync_message.properties == {
        "dealname": serialized_order["dealname"],
        "amount": serialized_order["amount"],
        "status": serialized_order["status"],
        "dealstage": serialized_order["dealstage"],
        "closedate": serialized_order["closedate"] or "",
        "coupon_code": serialized_order["coupon_code"] or "",
        "company": serialized_order["company"] or "",
        "payment_type": serialized_order["payment_type"] or "",
        "payment_transaction": serialized_order["payment_transaction"] or "",
        "discount_percent": serialized_order["discount_percent"] or "",
        "discount_amount": serialized_order["discount_amount"] or "",
        "order_type": serialized_order["order_type"],
        "pipeline": serialized_order["pipeline"],
        "unique_app_id": serialized_order["unique_app_id"],
    }


@pytest.mark.django_db
def test_make_b2b_deal_sync_message(hubspot_b2b_order):
    """Test make_b2b_deal_sync_message serializes a b2b order and returns a properly formatted sync message"""
    deal_sync_message = api.make_b2b_deal_sync_message(hubspot_b2b_order.id)
    serialized_order = B2BOrderToDealSerializer(hubspot_b2b_order).data
    assert deal_sync_message.properties == {
        "dealname": serialized_order["dealname"],
        "amount": serialized_order["amount"],
        "status": serialized_order["status"],
        "dealstage": serialized_order["dealstage"],
        "closedate": serialized_order["closedate"] or "",
        "coupon_code": serialized_order["coupon_code"] or "",
        "company": serialized_order["company"] or "",
        "payment_type": serialized_order["payment_type"] or "",
        "payment_transaction": serialized_order["payment_transaction"] or "",
        "discount_percent": serialized_order["discount_percent"] or "",
        "discount_amount": serialized_order["discount_amount"] or "",
        "order_type": serialized_order["order_type"],
        "num_seats": serialized_order["num_seats"],
        "pipeline": serialized_order["pipeline"],
        "unique_app_id": serialized_order["unique_app_id"],
    }


@pytest.mark.django_db
def test_make_b2b_line_sync_message(hubspot_b2b_order):
    """Test make_b2b_line_sync_message serializes a b2b line and returns a properly formatted sync message"""
    serialized_line = B2BOrderToLineItemSerializer(hubspot_b2b_order).data
    line_item_sync_message = api.make_b2b_line_sync_message(hubspot_b2b_order.id)
    assert line_item_sync_message.properties == {
        "name": serialized_line["name"],
        "hs_product_id": serialized_line["hs_product_id"],
        "status": serialized_line["status"],
        "product_id": serialized_line["product_id"],
        "price": serialized_line["price"],
        "quantity": serialized_line["quantity"],
        "unique_app_id": serialized_line["unique_app_id"],
    }


@pytest.mark.django_db
def test_make_line_item_sync_message(hubspot_order):
    """Test make_line_item_sync_message serializes an order line and returns a properly formatted sync message"""
    line = hubspot_order.lines.first()
    serialized_line = LineSerializer(line).data
    line_item_sync_message = api.make_line_item_sync_message(line.id)

    assert line_item_sync_message.properties == {
        "name": serialized_line["name"],
        "hs_product_id": serialized_line["hs_product_id"],
        "status": serialized_line["status"],
        "product_id": serialized_line["product_id"],
        "price": serialized_line["price"],
        "quantity": serialized_line["quantity"],
        "unique_app_id": serialized_line["unique_app_id"],
    }


@pytest.mark.django_db
def test_make_product_sync_message():
    """Test make_product_sync_message serializes a product and returns a properly formatted sync message"""
    product = ProductFactory()
    serialized_product = ProductSerializer(product).data
    product_sync_message = api.make_product_sync_message(product.id)

    assert product_sync_message.properties == {
        "name": serialized_product["name"],
        "price": serialized_product["price"],
        "description": serialized_product["description"],
        "unique_app_id": serialized_product["unique_app_id"],
    }


def test_sync_contact_with_hubspot(mock_hubspot_api):
    """Test that the hubspot CRM API is called properly for a contact sync"""
    user = UserFactory.create()
    api.sync_contact_with_hubspot(user.id)
    assert (
        api.HubspotObject.objects.get(
            object_id=user.id, content_type__model="user"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )
    mock_hubspot_api.return_value.crm.objects.basic_api.create.assert_called_once_with(
        simple_public_object_input=api.make_contact_sync_message(user.id),
        object_type=api.HubspotObjectType.CONTACTS.value,
    )


def test_sync_product_with_hubspot(mock_hubspot_api):
    """Test that the hubspot CRM API is called properly for a product sync"""
    product = ProductVersionFactory.create().product
    api.sync_product_with_hubspot(product.id)
    assert (
        api.HubspotObject.objects.get(
            object_id=product.id, content_type__model="product"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )
    mock_hubspot_api.return_value.crm.objects.basic_api.create.assert_called_once_with(
        simple_public_object_input=api.make_product_sync_message(product.id),
        object_type=api.HubspotObjectType.PRODUCTS.value,
    )


def test_sync_deal_with_hubspot(mocker, mock_hubspot_api, hubspot_order):
    """Test that the hubspot CRM API is called properly for a deal sync"""
    mock_sync_line = mocker.patch(
        "hubspot_xpro.api.sync_line_item_with_hubspot", autospec=True
    )
    api.sync_deal_with_hubspot(hubspot_order.id)

    mock_hubspot_api.return_value.crm.objects.basic_api.create.assert_called_once_with(
        simple_public_object_input=api.make_deal_sync_message(hubspot_order.id),
        object_type=api.HubspotObjectType.DEALS.value,
    )

    mock_sync_line.assert_any_call(hubspot_order.lines.first().id)

    assert (
        api.HubspotObject.objects.get(
            object_id=hubspot_order.id, content_type__model="order"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )


def test_sync_line_item_with_hubspot(mock_hubspot_api, hubspot_order, hubspot_order_id):
    """Test that the hubspot CRM API is called properly for a line_item sync"""
    line = hubspot_order.lines.first()
    api.sync_line_item_with_hubspot(line.id)
    assert (
        api.HubspotObject.objects.get(
            object_id=line.id, content_type__model="line"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )
    mock_hubspot_api.return_value.crm.objects.associations_api.create.assert_called_once_with(
        api.HubspotObjectType.LINES.value,
        FAKE_HUBSPOT_ID,
        api.HubspotObjectType.DEALS.value,
        hubspot_order_id,
        api.HubspotAssociationType.LINE_DEAL.value,
    )


def test_b2b_sync_deal_with_hubspot(mocker, mock_hubspot_api, hubspot_b2b_order):
    """Test that the hubspot CRM API is called properly for a b2b deal sync"""
    mock_sync_line = mocker.patch(
        "hubspot_xpro.api.sync_b2b_line_with_hubspot", autospec=True
    )
    mock_sync_contact = mocker.patch(
        "hubspot_xpro.api.sync_b2b_contact_with_hubspot", autospec=True
    )
    api.sync_b2b_deal_with_hubspot(hubspot_b2b_order.id)
    mock_sync_line.assert_called_once()
    mock_sync_contact.assert_called_once()

    mock_hubspot_api.return_value.crm.objects.basic_api.create.assert_called_once_with(
        simple_public_object_input=api.make_b2b_deal_sync_message(hubspot_b2b_order.id),
        object_type=api.HubspotObjectType.DEALS.value,
    )
    assert (
        api.HubspotObject.objects.get(
            object_id=hubspot_b2b_order.id, content_type__model="b2border"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )


def test_sync_b2b_line_with_hubspot(
    mock_hubspot_api, hubspot_b2b_order, hubspot_b2b_order_id
):
    """Test that the hubspot CRM API is called properly for a b2b line sync"""
    api.sync_b2b_line_with_hubspot(hubspot_b2b_order.id)
    mock_hubspot_api.return_value.crm.objects.associations_api.create.assert_called_once_with(
        api.HubspotObjectType.LINES.value,
        FAKE_HUBSPOT_ID,
        api.HubspotObjectType.DEALS.value,
        hubspot_b2b_order_id,
        api.HubspotAssociationType.LINE_DEAL.value,
    )
    assert (
        api.HubspotObject.objects.get(
            object_id=B2BLine.objects.first().id, content_type__model="b2bline"
        ).hubspot_id
        == FAKE_HUBSPOT_ID
    )


def test_sync_b2b_contact_with_hubspot(
    mock_hubspot_api, hubspot_b2b_order, hubspot_b2b_order_id
):
    """Test that the hubspot CRM API is called properly for a contact sync"""
    api.sync_b2b_contact_with_hubspot(hubspot_b2b_order.id)
    mock_hubspot_api.return_value.crm.objects.associations_api.create.assert_called_once_with(
        api.HubspotObjectType.DEALS.value,
        hubspot_b2b_order_id,
        api.HubspotObjectType.CONTACTS.value,
        FAKE_HUBSPOT_ID,
        api.HubspotAssociationType.DEAL_CONTACT.value,
    )


@pytest.mark.parametrize("match_all", [True, False])
def test_sync_contact_hubspot_ids_to_hubspot(mocker, mock_hubspot_api, match_all):
    """sync_contact_hubspot_ids_to_hubspot should create HubspotObjects and return True if all users matched"""
    matches = 3 if match_all else 2
    users = UserFactory.create_batch(3)
    contacts = [
        SimplePublicObjectFactory(properties={"email": user.email.capitalize()})
        for user in users[0:matches]
    ]
    mock_hubspot_api.return_value.crm.objects.basic_api.get_page.side_effect = [
        mocker.Mock(results=contacts, paging=None)
    ]
    assert api.sync_contact_hubspot_ids_to_db() is match_all
    assert HubspotObject.objects.filter(content_type__model="user").count() == matches


@pytest.mark.parametrize("multiple_emails", [True, False])
def test_sync_contact_hubspot_ids_alternate(mocker, mock_hubspot_api, multiple_emails):
    """sync_contact_hubspot_ids_to_hubspot should be able to match by alternate emails"""
    user = UserFactory.create()
    additional_emails = (
        f"{user.email.capitalize()};other_email@fake.edu"
        if multiple_emails
        else user.email
    )
    contacts = [
        SimplePublicObjectFactory(
            properties={
                "hs_additional_emails": additional_emails,
                "email": "fake@fake.edu",
            }
        )
    ]
    mock_hubspot_api.return_value.crm.objects.basic_api.get_page.side_effect = [
        mocker.Mock(results=contacts, paging=None)
    ]
    assert api.sync_contact_hubspot_ids_to_db() is True
    assert HubspotObject.objects.filter(content_type__model="user").count() == 1


@pytest.mark.parametrize("match_all", [True, False])
def test_sync_product_hubspot_ids_to_hubspot(mocker, mock_hubspot_api, match_all):
    """sync_product_hubspot_ids_to_db should create HubspotObjects and return True if all products matched"""
    matches = 3 if match_all else 2
    db_products = ProductFactory.create_batch(3)
    hs_products = [
        SimplePublicObjectFactory(properties={"name": api.format_product_name(product)})
        for product in db_products[0:matches]
    ]
    mock_hubspot_api.return_value.crm.objects.basic_api.get_page.side_effect = [
        mocker.Mock(results=hs_products, paging=None)
    ]
    assert api.sync_product_hubspot_ids_to_db() is match_all
    assert (
        HubspotObject.objects.filter(content_type__model="product").count() == matches
    )


def test_sync_product_hubspot_ids_dupe_names(mocker, mock_hubspot_api):
    """sync_product_hubspot_ids_to_db should handle dupe product names"""
    mocker.patch(
        "hubspot_xpro.api.format_product_name", return_value="Same Name Product"
    )
    db_product_versions = ProductVersionFactory.create_batch(2)
    hs_products = [
        SimplePublicObjectFactory(
            properties={"name": "Same Name Product", "price": pv.price}
        )
        for pv in db_product_versions
    ]
    mock_hubspot_api.return_value.crm.objects.basic_api.get_page.side_effect = [
        mocker.Mock(results=hs_products, paging=None)
    ]
    assert api.sync_product_hubspot_ids_to_db() is True
    assert HubspotObject.objects.filter(content_type__model="product").count() == 2


@pytest.mark.parametrize("match_all_lines", [True, False])
@pytest.mark.parametrize("match_all_deals", [True, False])
def test_sync_deal_hubspot_ids_to_hubspot(
    mocker, mock_hubspot_api, match_all_deals, match_all_lines
):
    """sync_deal_hubspot_ids_to_hubspot should create HubspotObjects and return True if all deals & lines matched"""
    deal_matches = 3 if match_all_deals else 2
    line_matches = 3 if match_all_lines else 2
    lines = LineFactory.create_batch(3, quantity=1)
    deals = [
        SimplePublicObjectFactory(
            properties={
                "dealname": f"XPRO-ORDER-{line.order.id}",
                "amount": str(line.order.total_price_paid),
            }
        )
        for line in lines[0:deal_matches]
    ]
    # This deal should be ignored
    SimplePublicObjectFactory(
        properties={
            "dealname": "XPRO-ORDER-MANUAL",
            "amount": "400.00",
        }
    )
    hs_products = [
        HubspotObjectFactory.create(
            content_object=line.product_version.product,
            content_type=ContentType.objects.get_for_model(Product),
            object_id=line.product_version.product.id,
        )
        for line in lines
    ]
    line_items = [
        SimplePublicObjectFactory(
            properties={"hs_product_id": hsp.hubspot_id, "quantity": 1}
        )
        for hsp in hs_products[0:line_matches]
    ]
    mock_hubspot_api.return_value.crm.objects.basic_api.get_page.side_effect = [
        mocker.Mock(results=deals, paging=None),  # deals
    ]
    mock_hubspot_api.return_value.crm.deals.associations_api.get_all.side_effect = [
        *[mocker.Mock(results=[SimplePublicObjectFactory()]) for _ in line_items],
        mocker.Mock(results=[]),
    ]  # associations
    mock_hubspot_api.return_value.crm.line_items.basic_api.get_by_id.side_effect = [
        SimplePublicObjectFactory(properties={"hs_product_id": hsp.hubspot_id})
        for hsp in hs_products[0:line_matches]
    ]  # line_item details
    assert api.sync_deal_hubspot_ids_to_db() is (match_all_lines and match_all_deals)
    assert (
        HubspotObject.objects.filter(content_type__model="order").count()
        == deal_matches
    )
    assert HubspotObject.objects.filter(content_type__model="line").count() == min(
        deal_matches, line_matches
    )
