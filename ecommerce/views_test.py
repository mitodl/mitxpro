"""ecommerce tests for views"""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus, urljoin

import factory
import faker
import pytest
from django.contrib.auth.models import Permission
from django.db.models import Count, Q
from django.test import Client
from django.urls import reverse
from pytest_lazy_fixtures import lf as lazy
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient

from affiliate.constants import AFFILIATE_QS_PARAM
from affiliate.factories import AffiliateFactory
from courses.factories import (
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramFactory,
    ProgramRunFactory,
)
from courses.models import CourseRun, Program
from ecommerce.api import create_unfulfilled_order, make_receipt_url
from ecommerce.constants import DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.exceptions import EcommerceException, ParseException
from ecommerce.factories import (
    CompanyFactory,
    CouponEligibilityFactory,
    CouponFactory,
    CouponPaymentFactory,
    LineFactory,
    ProductCouponAssignmentFactory,
    ProductVersionFactory,
)
from ecommerce.models import (
    Basket,
    BasketItem,
    BulkCouponAssignment,
    Company,
    Coupon,
    CouponEligibility,
    CouponPaymentVersion,
    CouponSelection,
    CourseRunSelection,
    DataConsentUser,
    Order,
    OrderAudit,
    Product,
    Receipt,
)
from ecommerce.serializers import (
    BasketSerializer,
    CompanySerializer,
    CouponSelectionSerializer,
    DataConsentUserSerializer,
    ProductSerializer,
    ProgramRunSerializer,
)
from ecommerce.serializers_test import datetime_format
from ecommerce.test_utils import unprotect_version_tables
from mitxpro.test_utils import assert_drf_json_equal
from mitxpro.utils import dict_without_keys, now_in_utc
from users.factories import UserFactory

CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
FAKE = faker.Factory.create()


pytestmark = pytest.mark.django_db


def render_json(serializer):
    """
    Convert serializer data to a JSON object.

    Args:
        serializer (Serializer): a serializer instance

    Returns:
        Object: a JSON object

    """
    return json.loads(JSONRenderer().render(serializer.data))


@pytest.fixture(autouse=True)
def ecommerce_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY
    settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL = CYBERSOURCE_SECURE_ACCEPTANCE_URL
    settings.ECOMMERCE_EMAIL = "ecommerce@example.com"
    settings.EDXORG_BASE_URL = "http://edx_base"


@pytest.fixture
def basket_client(basket_and_coupons):
    """DRF Client with logged in user with basket"""
    user = basket_and_coupons.basket_item.basket.user
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_unauthenticated(client):
    """
    Unauthenticated users can't use this API
    """
    resp = client.post(reverse("checkout"), {})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_creates_order(basket_client, mocker, basket_and_coupons):
    """
    An order is created using create_unfulfilled_order and a payload
    is generated using generate_cybersource_sa_payload
    """
    line = LineFactory.create(
        order__status=Order.CREATED, product_version=basket_and_coupons.product_version
    )
    order = line.order
    payload = {"a": "payload"}
    create_order_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )

    fake_ip = "195.0.0.1"
    mock_ip_call = mocker.patch(
        "ecommerce.views.get_client_ip", return_value=(fake_ip, True)
    )

    generate_payload_mock = mocker.patch(
        "ecommerce.views.generate_cybersource_sa_payload",
        autospec=True,
        return_value=payload,
    )
    resp = basket_client.post(reverse("checkout"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "payload": payload,
        "url": CYBERSOURCE_SECURE_ACCEPTANCE_URL,
        "method": "POST",
    }

    assert mock_ip_call.call_count == 1
    text_id = line.product_version.product.content_object.text_id
    assert create_order_mock.call_count == 1
    create_order_arg = create_order_mock.call_args[0][0]
    assert create_order_arg.basket == basket_and_coupons.basket
    assert generate_payload_mock.call_count == 1
    assert generate_payload_mock.call_args[0] == ()
    assert generate_payload_mock.call_args[1] == {
        "order": order,
        "receipt_url": make_receipt_url(
            base_url="http://testserver", readable_id=text_id
        ),
        "cancel_url": "http://testserver/checkout/",
        "ip_address": fake_ip,
    }


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_zero_price_checkout(  # noqa: PLR0913
    basket_client,
    mocker,
    basket_and_coupons,
    mock_hubspot_syncs,
    settings,
    hubspot_api_key,
):
    """
    If the order total is $0, we should just fulfill the order and direct the user to our order receipt page
    """
    settings.MITOL_HUBSPOT_API_PRIVATE_TOKEN = hubspot_api_key
    user = basket_and_coupons.basket_item.basket.user
    line = LineFactory.create(
        order__status=Order.CREATED,
        order__purchaser=user,
        order__total_price_paid=0,
        product_version=basket_and_coupons.product_version,
    )
    order = line.order
    create_order_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    enroll_user_mock = mocker.patch(
        "ecommerce.api.enroll_user_in_order_items", autospec=True
    )
    resp = basket_client.post(reverse("checkout"))
    assert (
        str(line)
        == f"Line for order #{line.order.id}, {line.product_version!s} (qty: {line.quantity})"
    )
    text_id = line.product_version.product.content_object.text_id

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "payload": {
            "transaction_id": f"T-{order.id}",
            "transaction_total": 0.0,
            "product_type": line.product_version.product.type_string,
            "courseware_id": text_id,
            "reference_number": f"REF-{order.id}",
        },
        "url": f"http://testserver/dashboard/?status=purchased&purchased={quote_plus(text_id)}",
        "method": "GET",
    }

    assert create_order_mock.call_count == 1
    create_order_arg = create_order_mock.call_args[0][0]
    assert create_order_arg.basket == basket_and_coupons.basket
    assert enroll_user_mock.call_count == 1
    assert enroll_user_mock.call_args[0] == (order,)
    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0
    if hubspot_api_key:
        mock_hubspot_syncs.order.assert_called_with(order.id)
    else:
        mock_hubspot_syncs.order.assert_not_called()


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_order_fulfilled(  # noqa: PLR0913
    mocker,
    settings,
    basket_client,
    basket_and_coupons,
    validated_basket,
    hubspot_api_key,
    mock_hubspot_syncs,
):
    """
    Test the happy case
    """
    settings.MITOL_HUBSPOT_API_PRIVATE_TOKEN = hubspot_api_key
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(validated_basket)

    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()

    data["req_reference_number"] = order.reference_number
    data["decision"] = "ACCEPT"

    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    enroll_user = mocker.patch(
        "ecommerce.api.enroll_user_in_order_items", autospec=True
    )
    resp = basket_client.post(reverse("order-fulfillment"), data=data)

    assert len(resp.content) == 0
    assert resp.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == Order.FULFILLED
    assert order.receipt_set.count() == 1
    receipt = order.receipt_set.first()
    assert str(receipt) == f"Receipt for order {receipt.order.id}"
    assert receipt.data == data
    enroll_user.assert_called_with(order)

    assert OrderAudit.objects.count() == 1
    order_audit = OrderAudit.objects.last()
    assert order_audit.order == order
    assert dict_without_keys(
        order_audit.data_before, "updated_on"
    ) == dict_without_keys(order.to_dict(), "updated_on")
    assert dict_without_keys(order_audit.data_after, "updated_on") == dict_without_keys(
        order.to_dict(), "updated_on"
    )

    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0

    if hubspot_api_key:
        mock_hubspot_syncs.order.assert_called_with(order.id)
    else:
        mock_hubspot_syncs.order.assert_not_called()


def test_order_affiliate(basket_client, mocker, basket_and_coupons):
    """
    The order view should pass an affiliate id into the order creation API function if an affiliate id exists
    in the session.
    """
    user = basket_and_coupons.basket_item.basket.user
    line = LineFactory.create(
        order__status=Order.CREATED,
        order__purchaser=user,
        order__total_price_paid=0,
        product_version=basket_and_coupons.product_version,
    )
    order = line.order
    mocker.patch("ecommerce.api.enroll_user_in_order_items", autospec=True)
    create_order_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    affiliate = AffiliateFactory.create()
    # Make an initial request to get the affiliate code in the session
    basket_client.get(f"/?{AFFILIATE_QS_PARAM}={affiliate.code}")
    resp = basket_client.post(reverse("checkout"))
    assert resp.status_code == status.HTTP_200_OK
    assert "affiliate_id" in create_order_mock.call_args_list[0][1]
    assert create_order_mock.call_args_list[0][1]["affiliate_id"] == affiliate.id


def test_missing_fields(basket_client, mocker):
    """
    If CyberSource POSTs with fields missing, we should at least save it in a receipt.
    It is very unlikely for Cybersource to POST invalid data but it also provides a way to test
    that we save a Receipt in the event of an error.
    """
    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    try:  # noqa: SIM105
        # Missing fields from Cybersource POST will cause a ParseException.
        # In this test we just care that we saved the data in Receipt for later
        # analysis.
        basket_client.post(reverse("order-fulfillment"), data=data)
    except ParseException:
        pass

    assert Order.objects.count() == 0
    assert Receipt.objects.count() == 1
    assert Receipt.objects.first().data == data


@pytest.mark.parametrize("decision", ["CANCEL", "something else"])
def test_not_accept(
    mocker, validated_basket, basket_client, basket_and_coupons, decision
):
    """
    If the decision is not ACCEPT then the order should be marked as failed
    """
    order = create_unfulfilled_order(validated_basket)

    data = {"req_reference_number": order.reference_number, "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = basket_client.post(reverse("order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.content) == 0
    order.refresh_from_db()
    assert Order.objects.count() == 1
    assert order.status == Order.FAILED


def test_ignore_duplicate_cancel(
    mocker, validated_basket, basket_client, basket_and_coupons
):
    """
    If the decision is CANCEL and we already have a duplicate failed order, don't change anything.
    """
    order = create_unfulfilled_order(validated_basket)
    order.status = Order.FAILED
    order.save()

    data = {"req_reference_number": order.reference_number, "decision": "CANCEL"}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = basket_client.post(reverse("order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK

    assert Order.objects.count() == 1
    assert Order.objects.get(id=order.id).status == Order.FAILED


@pytest.mark.parametrize(
    "order_status, decision",  # noqa: PT006
    [(Order.FAILED, "ERROR"), (Order.FULFILLED, "ERROR"), (Order.FULFILLED, "SUCCESS")],
)
def test_error_on_duplicate_order(  # noqa: PLR0913
    mocker, validated_basket, basket_client, basket_and_coupons, order_status, decision
):
    """If there is a duplicate message (except for CANCEL), raise an exception"""
    order = create_unfulfilled_order(validated_basket)
    order.status = order_status
    order.save()

    data = {"req_reference_number": order.reference_number, "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    with pytest.raises(EcommerceException) as ex:
        basket_client.post(reverse("order-fulfillment"), data=data)

    assert Order.objects.count() == 1
    assert Order.objects.get(id=order.id).status == order_status

    assert ex.value.args[0] == f"{order} is expected to have status 'created'"


def test_no_permission(basket_client, mocker):
    """
    If the permission class didn't give permission we shouldn't get access to the POST
    """
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=False
    )
    resp = basket_client.post(reverse("order-fulfillment"), data={})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_basket(basket_client, basket_and_coupons, mock_context, mocker):
    """Test the view that handles a get request for basket"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")

    basket = basket_and_coupons.basket

    resp = basket_client.get(reverse("basket_api"))
    program_data = resp.json()
    assert program_data == render_json(
        BasketSerializer(instance=basket, context=mock_context)
    )


@pytest.mark.parametrize(
    ("order_status", "expected_status_code"),
    [
        (Order.FULFILLED, status.HTTP_200_OK),
        (Order.CREATED, status.HTTP_404_NOT_FOUND),
        (Order.REFUNDED, status.HTTP_404_NOT_FOUND),
    ],
)
def test_get_order_configuration(user, user_client, order_status, expected_status_code):
    """Test the view that handles order receipts functions as expected"""
    line = LineFactory.create(order__status=order_status, order__purchaser=user)
    resp = user_client.get(reverse("order_receipt_api", kwargs={"pk": line.order.id}))
    assert resp.status_code == expected_status_code


def test_get_basket_new_user(basket_and_coupons, user, user_drf_client):
    """Test that the view creates a basket returns a 200 if a user doesn't already have a basket"""
    basket = Basket.objects.all().first()
    assert str(basket) == f"Basket for {str(basket.user)}"  # noqa: RUF010
    assert Basket.objects.filter(user=user).exists() is False
    resp = user_drf_client.get(reverse("basket_api"))
    assert resp.status_code == 200
    assert Basket.objects.count() == 2
    assert Basket.objects.filter(user=user).exists() is True


def test_patch_basket_new_user(basket_and_coupons, user, user_drf_client):
    """Test that the view creates a basket and patches it basket does not already exist for user"""
    assert Basket.objects.filter(user=user).exists() is False
    resp = user_drf_client.patch(reverse("basket_api"), {"items": []})
    assert resp.status_code == 200
    assert Basket.objects.filter(user=user).exists() is True


def test_patch_basket_new_item_with_product_id(
    basket_client, basket_and_coupons, mock_context, mocker
):
    """Test that a user can add an item to their basket"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    data = {"items": [{"product_id": basket_and_coupons.product_version.product.id}]}
    basket_item = BasketItem.objects.all().first()
    assert (
        str(basket_item)
        == f"BasketItem of product {basket_item.product!s} (qty: {basket_item.quantity})"
    )
    BasketItem.objects.all().delete()  # clear the basket first
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == render_json(
        BasketSerializer(instance=basket_and_coupons.basket, context=mock_context)
    )


def test_patch_basket_new_item_with_text_id(
    basket_client, basket_and_coupons, mock_context, mocker
):
    """Test that a user can add an item to their basket using the text id of the course run/program"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    data = {
        "items": [
            {
                "product_id": basket_and_coupons.product_version.product.content_object.text_id
            }
        ]
    }
    basket_item = BasketItem.objects.all().first()
    assert (
        str(basket_item)
        == f"BasketItem of product {basket_item.product!s} (qty: {basket_item.quantity})"
    )
    BasketItem.objects.all().delete()  # clear the basket first
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == render_json(
        BasketSerializer(instance=basket_and_coupons.basket, context=mock_context)
    )


def test_patch_basket_replace_item(basket_client, basket_and_agreement):
    """If a user changes the item in the basket it should clear away old selected runs and coupons"""
    new_product = ProductVersionFactory.create().product
    data = {"items": [{"product_id": new_product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == new_product.id
    assert items[0]["run_ids"] == []
    assert resp.json()["data_consents"] == []
    assert resp.json()["coupons"] == []

    assert CourseRunSelection.objects.count() == 0
    assert CouponSelection.objects.count() == 0


def test_patch_basket_replace_item_with_same(basket_client, basket_and_agreement):
    """
    If a user changes the item in the basket but it's the same as the old product,
    the same runs and coupons should be selected as before
    """
    data = {"items": [{"product_id": basket_and_agreement.product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == basket_and_agreement.product.id
    assert items[0]["run_ids"] == list(
        CourseRunSelection.objects.values_list("run", flat=True)
    )
    dcu = DataConsentUser.objects.get(user=basket_and_agreement.basket.user)
    assert (
        str(dcu)
        == f"DataConsentUser {dcu.user!s} for {dcu.agreement!s}, consent date {dcu.consent_date!s}"
    )
    assert resp.json()["data_consents"] == [DataConsentUserSerializer(dcu).data]
    selection = CouponSelection.objects.get(
        basket=basket_and_agreement.basket, coupon=basket_and_agreement.coupon
    )
    assert (
        str(selection)
        == f"CouponSelection for basket {selection.basket!s}, coupon {selection.coupon!s}"
    )
    assert resp.json()["coupons"] == [CouponSelectionSerializer(selection).data]


def test_patch_basket_multiple_products(basket_client, basket_and_coupons):
    """Test that an update with multiple products is rejected"""
    data = {"items": [{"product_id": 10}, {"product_id": 11}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Basket cannot contain more than one item" in resp_data["errors"]["items"]


def test_patch_basket_invalid_coupon_format(basket_client, basket_and_coupons):
    """Test that an update with an invalid coupon code format is rejected"""
    resp = basket_client.patch(
        reverse("basket_api"), type="json", data={"coupons": ["coupon code"]}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors") == {"coupons": "Invalid request"}


def test_patch_basket_multiple_coupons(basket_client, basket_and_coupons):
    """Test that an update with multiple coupons is rejected"""
    data = {"coupons": [{"code": "FOO"}, {"code": "BAR"}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert (
        resp_data["errors"]["coupons"] == "Basket cannot contain more than one coupon"
    )


def test_patch_basket_update_coupon_valid(
    basket_client, mock_context, basket_and_coupons, basket_and_agreement, mocker
):
    """Test that a valid coupon is successfully applied to the basket"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    basket = basket_and_coupons.basket
    original_coupon = basket_and_coupons.coupongroup_best.coupon
    original_basket = BasketSerializer(instance=basket, context=mock_context).data
    assert original_basket.get("coupons")[0].get("code") == original_coupon.coupon_code
    new_code = basket_and_coupons.coupongroup_worst.coupon.coupon_code
    data = {"coupons": [{"code": new_code}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items") == original_basket.get("items")
    assert CouponSelection.objects.get(basket=basket).coupon.coupon_code == new_code
    assert len(resp_data.get("coupons")) == 1
    assert resp_data.get("coupons")[0].get("code") == new_code
    assert resp_data["data_consents"] == []


def test_patch_basket_update_coupon_invalid(basket_client, basket_and_coupons):
    """Test that an invalid coupon is rejected"""
    bad_code = "FAKE_CODE"
    data = {"coupons": [{"code": bad_code}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert (
        resp_data["errors"]["coupons"]
        == f"Enrollment / Promotional Code '{bad_code}' is invalid"
    )


def test_patch_basket_clear_coupon_auto(
    basket_client, basket_and_coupons, mock_context, mocker
):
    """Test that an auto coupon is applied to basket when it exists and coupons cleared"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    basket = basket_and_coupons.basket
    auto_coupon = basket_and_coupons.coupongroup_worst.coupon
    original_basket = render_json(
        BasketSerializer(instance=basket, context=mock_context)
    )

    data = {"coupons": []}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == [
        {
            "code": auto_coupon.coupon_code,
            "amount": str(basket_and_coupons.coupongroup_worst.payment_version.amount),
            "discount_type": basket_and_coupons.coupongroup_worst.payment_version.discount_type,
            "targets": [basket_and_coupons.product_version.id],
        }
    ]
    assert resp_data.get("items") == original_basket.get("items")
    assert CouponSelection.objects.get(basket=basket).coupon == auto_coupon


def test_patch_basket_clear_coupon_no_auto(
    basket_client, basket_and_coupons, mock_context, mocker
):
    """Test that all coupons are cleared from basket"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    basket = basket_and_coupons.basket

    with unprotect_version_tables():
        auto_coupon_payment = basket_and_coupons.coupongroup_worst.payment_version
        auto_coupon_payment.automatic = False
        auto_coupon_payment.save()

    original_basket = BasketSerializer(instance=basket, context=mock_context).data
    assert len(original_basket.get("coupons")) == 1

    data = {"coupons": []}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == []
    assert resp_data.get("items") == original_basket.get("items")
    assert CouponSelection.objects.filter(basket=basket).first() is None


def test_patch_basket_update_valid_product_valid_coupon(
    basket_client, basket_and_coupons
):
    """Test that product is updated and coupon remains the same"""
    basket = basket_and_coupons.basket
    best_coupon = basket_and_coupons.coupongroup_best.coupon

    product_version = ProductVersionFactory()
    CouponEligibilityFactory(product=product_version.product, coupon=best_coupon)

    data = {"items": [{"product_id": product_version.product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items")[0].get("id") == product_version.id
    assert resp_data.get("coupons")[0].get("code") == best_coupon.coupon_code
    assert CouponSelection.objects.get(basket=basket).coupon == best_coupon


def test_patch_basket_update_valid_product_invalid_coupon_auto(
    basket_client, basket_and_coupons
):
    """Test that product is updated and invalid coupon replaced with auto coupon"""
    basket = basket_and_coupons.basket
    auto_coupon = basket_and_coupons.coupongroup_worst.coupon

    product_version = ProductVersionFactory()
    CouponEligibilityFactory(product=product_version.product, coupon=auto_coupon)

    data = {"items": [{"product_id": product_version.product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items")[0].get("id") == product_version.id
    assert resp_data.get("coupons")[0].get("code") == auto_coupon.coupon_code
    assert CouponSelection.objects.get(basket=basket).coupon == auto_coupon


@pytest.mark.parametrize("has_coupon", [True, False])
def test_patch_basket_update_valid_product_invalid_coupon_no_auto(
    basket_client, basket_and_coupons, has_coupon
):
    """Test that product is updated and invalid coupon removed"""
    basket = basket_and_coupons.basket
    product_version = ProductVersionFactory()

    if not has_coupon:
        basket.couponselection_set.all().delete()
    else:
        assert basket.couponselection_set.first() is not None
    data = {"items": [{"product_id": product_version.product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items")[0].get("id") == product_version.id
    assert resp_data.get("coupons") == []
    assert CouponSelection.objects.filter(basket=basket).first() is None


def test_patch_basket_update_invalid_product(basket_client, basket_and_coupons):
    """Test that invalid product id is rejected with no changes to basket"""
    bad_id = 9999
    data = {"items": [{"product_id": bad_id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert f"Invalid product id {bad_id}" in resp_data["errors"]["items"]


def test_patch_basket_update_active_inactive_product(basket_client, basket_and_coupons):
    """Test that inactive product id is rejected with no changes to basket but not the active ones."""
    product = ProductVersionFactory.create().product
    product.is_active = False
    product.save()
    data = {"items": [{"product_id": product.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert f"Invalid product id {product.id}" in resp_data["errors"]["items"]

    product.is_active = True
    product.save()
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK


def test_patch_basket_update_inactive_product(basket_client, basket_and_coupons):
    """Test that an inactive product id is rejected when updating the basket"""
    product = ProductVersionFactory.create(product__is_active=False).product
    text_id = product.content_object.text_id
    data = {"items": [{"product_id": text_id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert f"Invalid product id {text_id}" in resp_data["errors"]["items"]


@pytest.mark.parametrize("section", ["items", "coupons"])
def test_patch_basket_update_invalid_data(basket_client, basket_and_coupons, section):
    """Test that invalid product data is rejected with no changes to basket"""
    data = dict()  # noqa: C408
    data[section] = [{"foo": "bar"}]
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid request" in resp_data["errors"][section]


@pytest.mark.parametrize("data", [{"items": [], "coupons": []}, {"items": []}])
def test_patch_basket_clear_product(basket_client, basket_and_coupons, data):
    """Test that product, coupon, and runs are cleared"""
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == []
    assert resp_data.get("items") == []
    assert BasketItem.objects.count() == 0
    assert CourseRunSelection.objects.count() == 0


def test_patch_basket_nodata(basket_client, basket_and_coupons):
    """Test that a patch request with no items or coupons keys is invalidated"""
    resp = basket_client.patch(reverse("basket_api"), type="json", data={})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid request" in resp_data.get("errors")


@pytest.mark.parametrize("add_new_runs", [True, False])
def test_patch_basket_update_runs(basket_client, basket_and_coupons, add_new_runs):
    """A patch request with run ids should update and replace the existing run ids for that item"""
    product_version = basket_and_coupons.product_version
    product = product_version.product
    run1 = CourseRunFactory.create()
    run2 = CourseRunFactory.create(course__program=run1.course.program)
    product.content_object = run1.course.program
    product.save()

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={
            "items": [
                {
                    "product_id": product.id,
                    "run_ids": [run1.id, run2.id] if add_new_runs else [],
                }
            ]
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert sorted(resp_data["items"][0]["run_ids"]) == sorted(
        [run1.id, run2.id] if add_new_runs else []
    )


@pytest.mark.parametrize("is_selected", [True, False])
@pytest.mark.parametrize("is_program", [True, False])
def test_patch_basket_invalid_run(
    basket_client, basket_and_coupons, is_program, is_selected
):
    """A patch request with a run for a different product should result in a 400 error"""
    product_version = basket_and_coupons.product_version
    product = product_version.product
    run = CourseRunFactory.create()
    product.content_object = run.course.program if is_program else run
    product.save()

    # If the product is a course, create a new run on a different course which is invalid.
    # If the product is a program, create a new run on a different program.
    course_run_params = (
        dict(course__program=product.content_object.course.program)  # noqa: C408
        if not is_program
        else {}
    )
    other_course_run = CourseRunFactory.create(**course_run_params)
    other_run_id = other_course_run.id if is_selected else None

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={"items": [{"product_id": product.id, "run_ids": [other_run_id]}]},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["errors"] == {
        "runs": (
            "Some invalid courses were selected."
            if is_selected
            else "Each course must have a course run selection"
        )
    }


@pytest.mark.parametrize("multiple_for_program", [True, False])
def test_patch_basket_multiple_runs(
    basket_client, basket_and_coupons, multiple_for_program
):
    """A patch request for multiple runs for a course should result in a 400 error"""
    # Make basket item product a program, and select two runs for the basket
    product_version = basket_and_coupons.product_version
    product = product_version.product
    course = product.content_object.course
    program = course.program
    product.content_object = program
    product.save()

    run1 = basket_and_coupons.run
    if multiple_for_program:
        run2 = CourseRunFactory.create(course__program=program)
    else:
        run2 = CourseRunFactory.create(course=course)

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={"items": [{"product_id": product.id, "run_ids": [run1.id, run2.id]}]},
    )
    if multiple_for_program:
        assert resp.status_code == status.HTTP_200_OK
        assert sorted(
            CourseRunSelection.objects.filter(
                basket=basket_and_coupons.basket
            ).values_list("run", flat=True)
        ) == sorted([run1.id, run2.id])
    else:
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["errors"] == {
            "runs": "Only one run per course can be selected"
        }


def test_patch_basket_already_enrolled(basket_client, basket_and_coupons):
    """A patch request for a run for a course that the user has already enrolled in should result in a 400 error"""
    run = basket_and_coupons.run
    line = LineFactory.create(order__status=Order.FULFILLED)
    CourseRunEnrollmentFactory.create(
        run=run, user=basket_and_coupons.basket.user, order=line.order
    )

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={
            "items": [
                {
                    "product_id": basket_and_coupons.product_version.product.id,
                    "run_ids": [run.id],
                }
            ]
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["errors"] == {
        "runs": "User has already enrolled in one of the selected course runs"
    }


def test_patch_basket_other_user_enrolled(basket_client, basket_and_coupons):
    """A patch request for a course run that another user has already enrolled in should succeed"""
    run = basket_and_coupons.run
    order = LineFactory.create(order__status=Order.FULFILLED).order
    CourseRunEnrollmentFactory.create(run=run, user=order.purchaser, order=order)

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={
            "items": [
                {
                    "product_id": basket_and_coupons.product_version.product.id,
                    "run_ids": [run.id],
                }
            ]
        },
    )
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("as_owner", [True, False])
def test_patch_basket_data_consents(basket_and_agreement, as_owner):
    """Test that a patch request with DataConsentUser ids updates those objects with consent dates"""
    user = basket_and_agreement.basket.user if as_owner else UserFactory.create()
    client = APIClient()
    client.force_authenticate(user=user)
    consent_user = DataConsentUser.objects.get(
        agreement=basket_and_agreement.agreement,
        user=basket_and_agreement.basket.user,
        coupon=basket_and_agreement.coupon,
    )
    consent_user.consent_date = None
    consent_user.save()
    resp = client.patch(
        reverse("basket_api"), type="json", data={"data_consents": [consent_user.id]}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert (
        DataConsentUser.objects.filter(consent_date__isnull=not as_owner).exists()
        is True
    )
    if as_owner:
        assert resp.json()["data_consents"][0]["consent_date"] >= datetime.now(
            tz=UTC
        ).strftime("%Y-%m-%dT00:00:00Z")
    else:
        assert resp.json()["data_consents"] == []


def test_patch_basket_bad_data_consents(basket_and_agreement):
    """Test that a patch request with bad DataConsentUser raises a validation error"""
    user = basket_and_agreement.basket.user
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.patch(
        reverse("basket_api"), type="json", data={"data_consents": [9998, 9999]}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors") == {
        "data_consents": ["Invalid data consent id 9998,9999"]
    }


def test_patch_basket_external_product(basket_and_coupons):
    """Test that a patch request with external product results in a validation error"""
    user = basket_and_coupons.basket.user
    client = APIClient()
    client.force_authenticate(user=user)
    basket_and_coupons.run.course.is_external = True
    basket_and_coupons.run.course.save()

    resp = client.patch(
        reverse("basket_api"),
        type="json",
        data={"items": [{"product_id": basket_and_coupons.basket_item.product.id}]},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors") == [
        "We're sorry, This product cannot be purchased on this web site."
    ]


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_post_singleuse_coupons(admin_drf_client, single_use_coupon_json):
    """Test that the correct model objects are created for a batch of single-use coupons"""
    data = single_use_coupon_json
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    model_version = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    assert (
        str(model_version)
        == f"CouponPaymentVersion for {model_version.num_coupon_codes} of type {model_version.coupon_type}"
    )
    assert model_version.couponversion_set.count() == 5
    assert model_version.payment.coupon_set.count() == 5
    assert model_version.amount == data.get("amount")
    assert model_version.coupon_type == "single-use"
    assert model_version.payment_transaction == data.get("payment_transaction")
    assert Company.objects.filter(id=data.get("company")).first() is not None
    assert (
        CouponEligibility.objects.filter(product__in=data.get("product_ids")).count()
        == 15
    )


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_post_global_singleuse_coupons(admin_drf_client, single_use_coupon_json):
    """Test that the correct model objects are created for a batch of single-use coupons (global coupon)"""
    data = single_use_coupon_json
    data["is_global"] = True
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    model_version = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    assert (
        str(model_version)
        == f"CouponPaymentVersion for {model_version.num_coupon_codes} of type {model_version.coupon_type}"
    )
    assert model_version.couponversion_set.count() == 5
    assert model_version.payment.coupon_set.count() == 5
    assert model_version.amount == data.get("amount")
    assert model_version.coupon_type == "single-use"
    assert model_version.payment_transaction == data.get("payment_transaction")
    assert Company.objects.filter(id=data.get("company")).first() is not None
    assert (
        Coupon.objects.filter(payment=model_version.payment).first().is_global is True
    )
    assert (
        CouponEligibility.objects.filter(product__in=data.get("product_ids")).count()
        == 15
    )


@pytest.mark.parametrize(
    "discount_type, amount",  # noqa: PT006
    [
        [DISCOUNT_TYPE_PERCENT_OFF, 0.5],  # noqa: PT007
        [DISCOUNT_TYPE_DOLLARS_OFF, 50],  # noqa: PT007
    ],
)
def test_post_promo_coupon(admin_drf_client, promo_coupon_json, discount_type, amount):
    """Test that the correct model objects are created for a promo coupon"""
    data = promo_coupon_json
    data["discount_type"] = discount_type
    data["amount"] = amount
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    model_version = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    assert model_version.couponversion_set.count() == 1
    assert model_version.payment.coupon_set.count() == 1
    assert model_version.amount == data.get("amount")
    assert model_version.coupon_type == "promo"
    assert model_version.discount_type == discount_type
    assert model_version.payment_transaction == data.get("payment_transaction")
    assert model_version.payment.coupon_set.first().coupon_code == data.get(
        "coupon_code"
    )
    assert Company.objects.filter(id=data.get("company")).first() is not None
    assert (
        CouponEligibility.objects.filter(product__in=data.get("product_ids")).count()
        == 3
    )


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_post_global_promo_coupon(admin_drf_client, promo_coupon_json):
    """Test that the correct model objects are created for a promo coupon (global coupon)"""
    data = promo_coupon_json
    data["is_global"] = True
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    model_version = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    assert model_version.couponversion_set.count() == 1
    assert model_version.payment.coupon_set.count() == 1
    assert model_version.amount == data.get("amount")
    assert model_version.coupon_type == "promo"
    assert model_version.payment_transaction == data.get("payment_transaction")
    assert model_version.payment.coupon_set.first().coupon_code == data.get(
        "coupon_code"
    )
    assert Company.objects.filter(id=data.get("company")).first() is not None
    assert (
        Coupon.objects.filter(payment=model_version.payment).first().is_global is True
    )
    assert (
        CouponEligibility.objects.filter(product__in=data.get("product_ids")).count()
        == 3
    )


@pytest.mark.parametrize(
    "attribute,bad_value,error",  # noqa: PT006
    [
        [  # noqa: PT007
            "product_ids",
            [9998, 9999],
            "Product with id(s) 9998,9999 could not be found",
        ],
        [  # noqa: PT007
            "product_ids",
            [],
            "At least one product must be selected or coupon should be global.",
        ],
        ["name", "AlreadyExists", "This field must be unique."],  # noqa: PT007
        [  # noqa: PT007
            "coupon_code",
            "AlreadyExists",
            "Coupon code already exists in the platform.",
        ],
    ],
)
@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_create_promo_coupon_bad_product(
    admin_drf_client, promo_coupon_json, attribute, bad_value, error
):
    """Test that an error is returned if submitted coupon data is invalid"""
    CouponPaymentFactory.create(name="AlreadyExists")
    CouponFactory.create(coupon_code="AlreadyExists")
    data = promo_coupon_json
    data[attribute] = bad_value
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors")[0].get(attribute) == error


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_create_promo_coupon_no_payment_info(admin_drf_client, promo_coupon_json):
    """Test that a promo CouponPaymentVersion can be created without payment info"""
    data = promo_coupon_json
    payment_attrs = ("company", "payment_type", "payment_transaction")
    for attr in payment_attrs:
        data.pop(attr)
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    cpv = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    for attr in payment_attrs:
        assert getattr(cpv, attr) is None


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_create_singleuse_coupon_no_payment_info(
    admin_drf_client, single_use_coupon_json
):
    """Test that a single-use CouponPaymentVersion cannot be created without payment type, transaction info"""
    data = single_use_coupon_json
    payment_attrs = ("company", "payment_type", "payment_transaction")
    for attr in payment_attrs:
        data[attr] = None
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert {"payment_transaction": "This field may not be null."} in resp.json().get(
        "errors"
    )
    assert {"payment_type": "This field may not be null."} in resp.json().get("errors")


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_create_coupon_permission(user_drf_client, promo_coupon_json):
    """Test that non-admins cannot create coupons"""
    data = promo_coupon_json
    resp = user_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    (
        "add_coupon",
        "change_coupon",
        "expected_admin_status",
        "expected_coupons_status",
        "expected_deactivate_status",
    ),
    [
        (True, False, 200, 200, 403),
        (False, True, 200, 403, 200),
        (False, False, 403, 403, 403),
        (True, True, 200, 200, 200),
    ],
)
def test_ecommerce_restricted_view(  # noqa: PLR0913
    user,
    add_coupon,
    change_coupon,
    expected_admin_status,
    expected_coupons_status,
    expected_deactivate_status,
):
    """Test that the ecommerce restricted view is only accessible with the right permissions."""

    user.user_permissions.clear()
    if add_coupon:
        user.user_permissions.add(Permission.objects.get(codename="add_coupon"))
    if change_coupon:
        user.user_permissions.add(Permission.objects.get(codename="change_coupon"))

    client = Client()
    client.force_login(user)

    ecommerce_admin_url = reverse("ecommerce-admin")
    add_coupons_url = ecommerce_admin_url + "coupons"
    deactivate_coupons_url = ecommerce_admin_url + "deactivate-coupons"

    assert client.get(ecommerce_admin_url).status_code == expected_admin_status
    assert client.get(add_coupons_url).status_code == expected_coupons_status
    assert client.get(deactivate_coupons_url).status_code == expected_deactivate_status


def test_deactivate_coupons(mocker, admin_drf_client):
    """Test that the API successfully deactivates coupons based on coupon codes or payment names"""

    mock_deactivate_coupons = mocker.patch("ecommerce.views.deactivate_coupons")

    coupons = CouponFactory.create_batch(10)
    coupon_codes = [coupon.coupon_code for coupon in coupons[:5]]
    payment_names = [coupon.payment.name for coupon in coupons[5:]]
    mixed_coupons = coupon_codes + payment_names

    mock_deactivate_coupons.return_value = set(mixed_coupons)

    data = {"coupons": "\n".join(mixed_coupons)}

    assert all(coupon.enabled for coupon in coupons)

    response = admin_drf_client.put(reverse("coupon_api"), data=data, format="json")
    assert response.status_code == status.HTTP_200_OK

    expected_coupons = [coupon.id for coupon in coupons]
    actual_coupons = list(
        mock_deactivate_coupons.call_args[0][0].values_list("id", flat=True)
    )
    assert expected_coupons == actual_coupons

    assert response.data["num_of_coupons_deactivated"] == len(coupons)
    assert not response.data["skipped_codes"]


@pytest.mark.parametrize(
    "discount_type",
    (DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF),  # noqa: PT007
)
def test_coupon_csv_view(admin_client, admin_drf_client, single_use_coupon_json):
    """Test that a valid csv response is returned for a CouponPaymentVersion"""
    data = single_use_coupon_json
    api_response = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    cpv = CouponPaymentVersion.objects.get(id=api_response.json().get("id"))
    csv_response = admin_client.get(
        reverse("coupons_csv", kwargs={"version_id": cpv.id})
    )
    assert csv_response.status_code == 200
    rows = [line.split(",") for line in csv_response.content.decode().split()]
    assert rows[0] == ["code"]
    codes = [row[0] for row in rows[1:]]
    assert sorted(codes) == sorted(
        cpv.couponversion_set.values_list("coupon__coupon_code", flat=True)
    )


def test_bulk_assignment_csv_view(settings, admin_client, admin_drf_client):
    """Test that the bulk assignment CSV includes the correct product coupon assignment data"""
    settings.SITE_BASE_URL = "http://test.com/"

    bulk_assignment = BulkCouponAssignment.objects.create()
    individual_assignments = ProductCouponAssignmentFactory.create_batch(
        3, bulk_assignment=bulk_assignment
    )
    assert (
        str(individual_assignments[0])
        == f"ProductCouponAssignment for {individual_assignments[0].email}, product coupon {individual_assignments[0].product_coupon_id} (redeemed: {individual_assignments[0].redeemed})"
    )
    csv_response = admin_client.get(
        reverse("bulk_assign_csv", kwargs={"bulk_assignment_id": bulk_assignment.id})
    )
    assert csv_response.status_code == 200
    rows = [line.split(",") for line in csv_response.content.decode().split()]
    assert len(rows) == (len(individual_assignments) + 1)
    assert rows[0] == ["email", "enrollment_url", "coupon_code"]
    data_rows = rows[1:]
    assert sorted(data_rows) == sorted(
        [
            [
                assignment.email,
                f"http://test.com/checkout/?is_voucher_applied=False&product={assignment.product_coupon.product.id}&code={assignment.product_coupon.coupon.coupon_code}",
                assignment.product_coupon.coupon.coupon_code,
            ]
            for assignment in individual_assignments
        ]
    )


@pytest.mark.parametrize(
    "url_name,url_kwarg_name,test_client,expected_status_code",  # noqa: PT006
    [
        [  # noqa: PT007
            "coupons_csv",
            "version_id",
            lazy("admin_client"),
            status.HTTP_404_NOT_FOUND,
        ],
        [  # noqa: PT007
            "coupons_csv",
            "version_id",
            lazy("user_client"),
            status.HTTP_403_FORBIDDEN,
        ],
        [  # noqa: PT007
            "bulk_assign_csv",
            "bulk_assignment_id",
            lazy("admin_client"),
            status.HTTP_404_NOT_FOUND,
        ],
        [  # noqa: PT007
            "bulk_assign_csv",
            "bulk_assignment_id",
            lazy("user_client"),
            status.HTTP_403_FORBIDDEN,
        ],
    ],
)
def test_csv_views_errors(url_name, url_kwarg_name, test_client, expected_status_code):
    """
    Test that the views that return a CSV containing user ecommerce data is protected and returns a 404 if
    a non-existent id is requested
    """
    response = test_client.get(reverse(url_name, kwargs={url_kwarg_name: 9999}))
    assert response.status_code == expected_status_code


def test_products_viewset_list(user_drf_client, coupon_product_ids):
    """Test that the ProductViewSet returns all products"""
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert {product.get("id") for product in products} == set(coupon_product_ids)
    for product in products:
        assert_drf_json_equal(
            product,
            ProductSerializer(instance=Product.objects.get(id=product.get("id"))).data,
        )


def test_products_viewset_list_ordering(user_drf_client):
    """
    Test that the ProductViewSet returns all products ordered alphabetically
    by course/program title
    """
    programs = ProgramFactory.create_batch(
        2, title=factory.Iterator(["Z Program", "A Program"])
    )
    runs = CourseRunFactory.create_batch(
        2,
        course__title=factory.Iterator(["Z Course", "A Course"]),
        course__program=factory.Iterator(programs),
    )
    ProgramRunFactory.create_batch(2, program=factory.Iterator(programs))
    ProductVersionFactory.create_batch(
        4, product__content_object=factory.Iterator(runs + programs)
    )
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    product_object_ids = [
        product["latest_version"]["object_id"] for product in products
    ]
    # Results should be returned with programs before course runs, then alphabetized by title
    assert product_object_ids == [
        programs[1].id,
        programs[0].id,
        runs[1].id,
        runs[0].id,
    ]
    assert [product["latest_version"]["type"] for product in products] == [
        "program",
        "program",
        "courserun",
        "courserun",
    ]


def test_products_viewset_valid_courses(user_drf_client):
    """Test that the ProductViewSet returns only valid course products"""

    runs = CourseRunFactory.create_batch(2)
    ProductVersionFactory.create_batch(
        2, product__content_object=factory.Iterator(runs)
    )
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert products != []
    # For all the course run products, enrollment_end should not have passed
    for product in products:
        enrollment_end = product["content_object"]["enrollment_end"]
        assert enrollment_end is None or enrollment_end > now_in_utc().strftime(
            datetime_format
        )


def test_products_viewset_valid_programs(user_drf_client):
    """Test that the ProductViewSet returns only valid programs products"""
    now = now_in_utc()
    programs = ProgramFactory.create_batch(2)
    runs = CourseRunFactory.create_batch(2, course__program=factory.Iterator(programs))
    ProgramRunFactory.create_batch(
        2,
        program=factory.Iterator(programs),
        end_date=factory.Iterator([None, now + timedelta(1)]),
    )
    ProductVersionFactory.create_batch(
        4, product__content_object=factory.Iterator(runs + programs)
    )
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    expired_courseruns = CourseRun.objects.filter(enrollment_end__lt=now).values_list(
        "id", flat=True
    )
    program_ids = [
        product["latest_version"]["object_id"]
        for product in products
        if product["product_type"] == "program"
    ]
    # For all the programs in the list there should be on enrollable course run for each associated course
    assert set(program_ids) == {programs[0].id, programs[1].id}
    for program_id in program_ids:
        program = Program.objects.get(pk=program_id)
        count = (
            program.courses.annotate(
                runs=Count("courseruns", filter=~Q(courseruns__in=expired_courseruns))
            )
            .filter(runs=0)
            .count()
        )
        assert count == 0


def test_products_viewset_external_courses(user_drf_client):
    """Test that the ProductViewSet returns contains only internal course products"""
    external_runs = CourseRunFactory.create_batch(
        2,
        course__is_external=True,
        start_date=now_in_utc() - timedelta(hours=2),
        end_date=now_in_utc() + timedelta(hours=2),
    )
    external_programs = ProgramFactory.create_batch(2, is_external=True)

    ProductVersionFactory.create_batch(
        4, product__content_object=factory.Iterator(external_runs + external_programs)
    )

    # External products should not be part of Products API
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert products == []

    # Only internal products should not be part of Products API
    internal_runs = CourseRunFactory.create_batch(
        2,
        start_date=now_in_utc() - timedelta(hours=2),
        end_date=now_in_utc() + timedelta(hours=2),
    )
    internal_programs_runs = ProgramRunFactory.create_batch(2)

    internal_product_versions = ProductVersionFactory.create_batch(
        4,
        product__content_object=factory.Iterator(
            internal_runs
            + [
                internal_program_run.program
                for internal_program_run in internal_programs_runs
            ]
        ),
    )

    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    generated_product_ids = [
        product_version.product.id for product_version in internal_product_versions
    ]
    response_product_ids = [product.get("id") for product in products]

    assert set(generated_product_ids) == set(response_product_ids)


def test_products_api_returns_public_products(user_drf_client):
    """Test that the ProductViewSet returns all public products"""
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert len(products) == Product.objects.filter(is_private=False).count()


def test_products_viewset_list_missing_versions(user_drf_client):
    """ProductViewSet should exclude Product without any ProductVersion"""
    product = ProductVersionFactory.create().product
    assert len(user_drf_client.get(reverse("products_api-list")).json()) == 1
    with unprotect_version_tables():
        product.latest_version.delete()
    assert len(user_drf_client.get(reverse("products_api-list")).json()) == 0


def test_products_viewset_detail(user_drf_client, coupon_product_ids):
    """Test that the ProductViewSet returns details for a product"""
    response = user_drf_client.get(
        reverse("products_api-detail", kwargs={"pk": coupon_product_ids[0]})
    )
    assert response.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        response.json(),
        ProductSerializer(instance=Product.objects.get(id=coupon_product_ids[0])).data,
    )


def test_products_viewset_expired_programs(user_drf_client):
    """Test that the ProductViewSet returns only valid programs products and excludes the expired programs correctly"""
    now = now_in_utc()
    programs = ProgramFactory.create_batch(4)
    runs = CourseRunFactory.create_batch(2, course__program=factory.Iterator(programs))
    ProgramRunFactory.create_batch(
        3,
        program=factory.Iterator(programs[:3]),
        end_date=factory.Iterator([None, now + timedelta(1)]),
    )
    ProgramRunFactory.create(program=programs[3], end_date=now - timedelta(1))

    ProductVersionFactory.create_batch(
        6, product__content_object=factory.Iterator(runs + programs)
    )
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    program_ids = [
        product["latest_version"]["object_id"]
        for product in products
        if product["product_type"] == "program"
    ]
    # assert non expired programs are in list.
    assert set(program_ids) == {programs[0].id, programs[1].id, programs[2].id}

    # Expired program should be excluded.
    assert programs[3].id not in program_ids


@pytest.mark.django_db
def test_products_viewset_performance(
    user_drf_client, coupon_product_ids, django_assert_num_queries
):
    """Test that the ProductViewSet returns the expected number of queries hit."""
    with django_assert_num_queries(10):
        response = user_drf_client.get(
            reverse("products_api-detail", kwargs={"pk": coupon_product_ids[0]})
        )
        assert response.status_code == status.HTTP_200_OK
        assert_drf_json_equal(
            response.json(),
            ProductSerializer(
                instance=Product.objects.get(id=coupon_product_ids[0])
            ).data,
        )


def test_products_viewset_post_forbidden(admin_drf_client):
    """Test that post requests to the products API viewset is not allowed"""
    response = admin_drf_client.post(reverse("products_api-list"), data={})
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_products_viewset_nested_param(user_drf_client, coupon_product_ids):
    """Test that the ProductViewSet returns details for a product"""
    response = user_drf_client.get(
        urljoin(reverse("products_api-list"), "?nested=false")
    )
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert {product.get("id") for product in products} == set(coupon_product_ids)
    for product in products:
        assert_drf_json_equal(
            product,
            ProductSerializer(instance=Product.objects.get(id=product.get("id"))).data,
        )


def test_companies_viewset_list(user_drf_client):
    """Test that the CompanyViewSet returns all companies"""
    companies = CompanyFactory.create_batch(3)
    response = user_drf_client.get(reverse("companies_api-list"))
    assert response.status_code == status.HTTP_200_OK
    companies_list = response.json()
    assert {company.get("id") for company in companies_list} == {
        company.id for company in companies
    }
    for company in companies_list:
        assert company == CompanySerializer(instance=company).data


def test_companies_viewset_detail(user_drf_client):
    """Test that the CompanyViewSet returns details for a company"""
    company = CompanyFactory.create()
    response = user_drf_client.get(
        reverse("companies_api-detail", kwargs={"pk": company.id})
    )
    assert str(company) == f"Company {company.name}"
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == CompanySerializer(instance=company).data


def test_companies_viewset_forbidden():
    """Test that an anonymous user cannot access the companies list"""
    client = APIClient()
    response = client.get(reverse("companies_api-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_companies_viewset_post_forbidden(admin_drf_client):
    """Test that post requests to the companies API viewset is not allowed"""
    response = admin_drf_client.post(reverse("companies_api-list"), data={})
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_patch_basket_expired_run(basket_client, basket_and_coupons):
    """A patch request with expired run ids should show the error"""
    product_version = basket_and_coupons.product_version
    product = product_version.product
    now = now_in_utc()
    course_run = CourseRunFactory.create(
        enrollment_start=(now - timedelta(days=150)),
        enrollment_end=(now - timedelta(days=120)),
        start_date=(now - timedelta(days=120)),
        end_date=(now - timedelta(days=10)),
    )
    product.content_object = course_run
    product.save()

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={"items": [{"product_id": product.id, "run_ids": [course_run.id]}]},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert sorted(resp_data["errors"]) == [
        "We're sorry, this course or program is no longer available for enrollment."
    ]


def test_program_runs_api():
    """Program run api should return the correct data"""
    product_version = ProductVersionFactory(
        product__content_object=ProgramFactory.create()
    )
    program_runs = ProgramRunFactory.create_batch(
        3, program=product_version.product.content_object
    )
    client = APIClient()
    resp = client.get(
        reverse(
            "program_runs_api-list",
            kwargs={"program_product_id": product_version.product.id},
        )
    )
    serialized_data = ProgramRunSerializer(program_runs, many=True).data
    assert resp.status_code == status.HTTP_200_OK
    assert sorted(resp.data, key=lambda item: item["id"]) == sorted(
        serialized_data, key=lambda item: item["id"]
    )
