"""ecommerce tests for views"""
import json

from django.urls import reverse
import faker
import pytest
import rest_framework.status as status  # pylint: disable=useless-import-alias
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient

from ecommerce.api import create_unfulfilled_order, make_reference_id
from ecommerce.exceptions import EcommerceException
from ecommerce.factories import (
    CouponEligibilityFactory,
    LineFactory,
    ProductVersionFactory,
)
from ecommerce.models import Basket, CouponSelection, Order, OrderAudit, Receipt
from ecommerce.serializers import BasketSerializer

CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
CYBERSOURCE_REFERENCE_PREFIX = "fake"
CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
FAKE = faker.Factory.create()


pytestmark = pytest.mark.django_db
# pylint: disable=redefined-outer-name,unused-argument


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
    settings.CYBERSOURCE_REFERENCE_PREFIX = CYBERSOURCE_REFERENCE_PREFIX
    settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL = CYBERSOURCE_SECURE_ACCEPTANCE_URL
    settings.ECOMMERCE_EMAIL = "ecommerce@example.com"
    settings.EDXORG_BASE_URL = "http://edx_base"


# pylint: disable=redefined-outer-name
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
    user = basket_and_coupons.basket_item.basket.user
    order = LineFactory.create(order__status=Order.CREATED).order
    payload = {"a": "payload"}
    create_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    generate_mock = mocker.patch(
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

    assert create_mock.call_count == 1
    assert create_mock.call_args[0] == (user,)
    assert generate_mock.call_count == 1
    assert generate_mock.call_args[0] == (order, "http://testserver/")


def test_zero_price_checkout(basket_client, mocker, basket_and_coupons):
    """
    If the order total is $0, we should just fulfill the order and direct the user to our order receipt page
    """
    user = basket_and_coupons.basket_item.basket.user
    order = LineFactory.create(
        order__status=Order.CREATED, product_version__price=0
    ).order
    create_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    enroll_user_mock = mocker.patch(
        "ecommerce.views.enroll_user_on_success", autospec=True
    )
    resp = basket_client.post(reverse("checkout"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": "http://testserver/", "method": "GET"}

    assert create_mock.call_count == 1
    assert create_mock.call_args[0] == (user,)

    assert enroll_user_mock.call_count == 1
    assert enroll_user_mock.call_args[0] == (order,)


def test_zero_price_checkout_failed_enroll(basket_client, mocker, basket_and_coupons):
    """
    If we do a $0 checkout but the enrollment fails, we should send an email but leave the order as fulfilled
    """
    user = basket_and_coupons.basket_item.basket.user

    order = LineFactory.create(
        order__status=Order.CREATED, product_version__price=0
    ).order
    create_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    enroll_user_mock = mocker.patch(
        "ecommerce.views.enroll_user_on_success", side_effect=KeyError
    )
    resp = basket_client.post(reverse("checkout"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": "http://testserver/", "method": "GET"}

    assert create_mock.call_count == 1
    assert create_mock.call_args[0] == (user,)

    assert enroll_user_mock.call_count == 1
    assert enroll_user_mock.call_args[0] == (order,)


def test_order_fulfilled(basket_client, mocker, basket_and_coupons):
    """
    Test the happy case
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)
    data_before = order.to_dict()

    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()

    data["req_reference_number"] = make_reference_id(order)
    data["decision"] = "ACCEPT"

    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    enroll_user = mocker.patch("ecommerce.views.enroll_user_on_success", autospec=True)
    resp = basket_client.post(reverse("order-fulfillment"), data=data)

    assert len(resp.content) == 0
    assert resp.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == Order.FULFILLED
    assert order.receipt_set.count() == 1
    assert order.receipt_set.first().data == data
    enroll_user.assert_called_with(order)

    assert OrderAudit.objects.count() == 2
    order_audit = OrderAudit.objects.last()
    assert order_audit.order == order
    assert order_audit.data_before == data_before
    assert order_audit.data_after == order.to_dict()


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
    try:
        # Missing fields from Cybersource POST will cause the KeyError.
        # In this test we just care that we saved the data in Receipt for later
        # analysis.
        basket_client.post(reverse("order-fulfillment"), data=data)
    except KeyError:
        pass

    assert Order.objects.count() == 0
    assert Receipt.objects.count() == 1
    assert Receipt.objects.first().data == data


def test_failed_enroll(basket_client, mocker, basket_and_coupons):
    """
    If we fail to enroll in edX, the order status should be fulfilled but an error email should be sent
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)

    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()

    data["req_reference_number"] = make_reference_id(order)
    data["decision"] = "ACCEPT"

    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    mocker.patch("ecommerce.views.enroll_user_on_success", side_effect=KeyError)
    basket_client.post(reverse("order-fulfillment"), data=data)

    assert Order.objects.count() == 1
    # An enrollment failure should not prevent the order from being fulfilled
    order = Order.objects.first()
    assert order.status == Order.FULFILLED


@pytest.mark.parametrize("decision", ["CANCEL", "something else"])
def test_not_accept(mocker, basket_client, basket_and_coupons, decision):
    """
    If the decision is not ACCEPT then the order should be marked as failed
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)

    data = {"req_reference_number": make_reference_id(order), "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = basket_client.post(reverse("order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.content) == 0
    order.refresh_from_db()
    assert Order.objects.count() == 1
    assert order.status == Order.FAILED


def test_ignore_duplicate_cancel(basket_client, mocker, basket_and_coupons):
    """
    If the decision is CANCEL and we already have a duplicate failed order, don't change anything.
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)
    order.status = Order.FAILED
    order.save()

    data = {"req_reference_number": make_reference_id(order), "decision": "CANCEL"}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = basket_client.post(reverse("order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK

    assert Order.objects.count() == 1
    assert Order.objects.get(id=order.id).status == Order.FAILED


@pytest.mark.parametrize(
    "order_status, decision",
    [(Order.FAILED, "ERROR"), (Order.FULFILLED, "ERROR"), (Order.FULFILLED, "SUCCESS")],
)
def test_error_on_duplicate_order(
    basket_client, mocker, basket_and_coupons, order_status, decision
):
    """If there is a duplicate message (except for CANCEL), raise an exception"""
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)
    order.status = order_status
    order.save()

    data = {"req_reference_number": make_reference_id(order), "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    with pytest.raises(EcommerceException) as ex:
        basket_client.post(reverse("order-fulfillment"), data=data)

    assert Order.objects.count() == 1
    assert Order.objects.get(id=order.id).status == order_status

    assert ex.value.args[0] == "Order {id} is expected to have status 'created'".format(
        id=order.id
    )


def test_no_permission(basket_client, mocker):
    """
    If the permission class didn't give permission we shouldn't get access to the POST
    """
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=False
    )
    resp = basket_client.post(reverse("order-fulfillment"), data={})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_basket(basket_client, basket_and_coupons):
    """Test the view that handles a get request for basket"""
    basket = basket_and_coupons.basket

    resp = basket_client.get(reverse("basket_api"))
    program_data = resp.json()
    assert program_data == render_json(BasketSerializer(instance=basket))


def test_get_basket_new_user(basket_and_coupons, user, user_drf_client):
    """Test that the view creates a basket returns a 200 if a user doesn't already have a basket"""
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


def test_patch_basket_multiple_products(basket_client, basket_and_coupons):
    """ Test that an update with multiple products is rejected """
    data = {"items": [{"id": 10}, {"id": 11}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Basket cannot contain more than one item" in resp_data.get("errors")


def test_patch_basket_multiple_coupons(basket_client, basket_and_coupons):
    """ Test that an update with multiple coupons is rejected """
    data = {"coupons": [{"code": "FOO"}, {"code": "BAR"}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Basket cannot contain more than one coupon" in resp_data.get("errors")


def test_patch_basket_update_coupon_valid(basket_client, basket_and_coupons):
    """ Test that a valid coupon is successfully applied to the basket """
    basket = basket_and_coupons.basket
    original_coupon = basket_and_coupons.coupongroup_best.coupon
    original_basket = BasketSerializer(basket).data
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


def test_patch_basket_update_coupon_invalid(basket_client, basket_and_coupons):
    """ Test that an invalid coupon is rejected"""
    bad_code = "FAKE_CODE"
    data = {"coupons": [{"code": bad_code}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Coupon code {} is invalid".format(bad_code) in resp_data.get("errors")


def test_patch_basket_clear_coupon_auto(basket_client, basket_and_coupons):
    """ Test that an auto coupon is applied to basket when it exists and coupons cleared """
    basket = basket_and_coupons.basket
    auto_coupon = basket_and_coupons.coupongroup_worst.coupon
    original_basket = render_json(BasketSerializer(instance=basket))

    data = {"coupons": []}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == [
        {
            "code": auto_coupon.coupon_code,
            "amount": basket_and_coupons.coupongroup_worst.invoice_version.amount,
            "targets": [basket_and_coupons.product_version.id],
        }
    ]
    assert resp_data.get("items") == original_basket.get("items")
    assert CouponSelection.objects.get(basket=basket).coupon == auto_coupon


def test_patch_basket_clear_coupon_no_auto(basket_client, basket_and_coupons):
    """ Test that all coupons are cleared from basket  """
    basket = basket_and_coupons.basket

    auto_coupon_invoice = basket_and_coupons.coupongroup_worst.invoice_version
    auto_coupon_invoice.automatic = False
    auto_coupon_invoice.save()

    original_basket = BasketSerializer(instance=basket).data
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
    """ Test that product is updated and coupon remains the same """
    basket = basket_and_coupons.basket
    best_coupon = basket_and_coupons.coupongroup_best.coupon

    product_version = ProductVersionFactory()
    CouponEligibilityFactory(product=product_version.product, coupon=best_coupon)

    data = {"items": [{"id": product_version.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items")[0].get("id") == product_version.id
    assert resp_data.get("coupons")[0].get("code") == best_coupon.coupon_code
    assert CouponSelection.objects.get(basket=basket).coupon == best_coupon


def test_patch_basket_update_valid_product_invalid_coupon_auto(
    basket_client, basket_and_coupons
):
    """ Test that product is updated and invalid coupon replaced with auto coupon """
    basket = basket_and_coupons.basket
    auto_coupon = basket_and_coupons.coupongroup_worst.coupon

    product_version = ProductVersionFactory()
    CouponEligibilityFactory(product=product_version.product, coupon=auto_coupon)

    data = {"items": [{"id": product_version.id}]}
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
    """ Test that product is updated and invalid coupon removed """
    basket = basket_and_coupons.basket
    product_version = ProductVersionFactory()

    if not has_coupon:
        basket.couponselection_set.all().delete()
    else:
        assert basket.couponselection_set.first() is not None
    data = {"items": [{"id": product_version.id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("items")[0].get("id") == product_version.id
    assert resp_data.get("coupons") == []
    assert CouponSelection.objects.filter(basket=basket).first() is None


def test_patch_basket_update_invalid_product(basket_client, basket_and_coupons):
    """ Test that invalid product id is rejected with no changes to basket """
    bad_id = 9999
    data = {"items": [{"id": bad_id}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid product version id {}".format(bad_id) in resp_data.get("errors")


@pytest.mark.parametrize("section", ["items", "coupons"])
def test_patch_basket_update_invalid_data(basket_client, basket_and_coupons, section):
    """ Test that invalid product data is rejected with no changes to basket """
    data = dict()
    data[section] = [{"foo": "bar"}]
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid request" in resp_data.get("errors")


@pytest.mark.parametrize("data", [{"items": [], "coupons": []}, {"items": []}])
def test_patch_basket_clear_product(basket_client, basket_and_coupons, data):
    """ Test that both product and coupon are cleared  """
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == []
    assert resp_data.get("items") == []


def test_patch_basket_nodata(basket_client, basket_and_coupons):
    """ Test that a patch request with no items or coupons keys is invalidated  """
    resp = basket_client.patch(reverse("basket_api"), type="json", data={})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid request" in resp_data.get("errors")
