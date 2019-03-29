"""ecommerce tests for views"""
from django.urls import reverse
import faker
import pytest
import rest_framework.status as status  # pylint: disable=useless-import-alias
from rest_framework.test import APIClient

from ecommerce.api import create_unfulfilled_order, make_reference_id
from ecommerce.exceptions import EcommerceException
from ecommerce.factories import LineFactory
from ecommerce.models import Order, OrderAudit, Receipt


CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
CYBERSOURCE_REFERENCE_PREFIX = "fake"
CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
FAKE = faker.Factory.create()

pytestmark = pytest.mark.django_db


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
