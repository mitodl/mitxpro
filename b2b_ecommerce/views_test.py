"""Views for b2b_ecommerce"""
from urllib.parse import urljoin
import uuid

from django.urls import reverse
import faker
import pytest
from rest_framework import status

from b2b_ecommerce.factories import B2BOrderFactory, ProductVersionFactory
from b2b_ecommerce.models import B2BOrder, B2BOrderAudit, B2BReceipt
from ecommerce.exceptions import EcommerceException
from ecommerce.factories import CouponVersionFactory
from ecommerce.serializers import ProductVersionSerializer
from mitxpro.utils import dict_without_keys


CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
CYBERSOURCE_REFERENCE_PREFIX = "fake"
CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
FAKE = faker.Factory.create()


pytestmark = pytest.mark.django_db
# pylint: disable=redefined-outer-name,unused-argument,too-many-lines


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


def test_create_order(client, mocker):
    """
    An order is created using and a payload
    is generated using generate_cybersource_sa_payload
    """
    payload = {"a": "payload"}
    generate_mock = mocker.patch(
        "b2b_ecommerce.views.generate_b2b_cybersource_sa_payload",
        autospec=True,
        return_value=payload,
    )
    product_version = ProductVersionFactory.create()
    num_seats = 10
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": num_seats,
            "email": "b@example.com",
            "product_version_id": product_version.id,
        },
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "payload": payload,
        "url": CYBERSOURCE_SECURE_ACCEPTANCE_URL,
        "method": "POST",
    }

    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    assert order.status == B2BOrder.CREATED
    assert order.total_price == product_version.price * num_seats
    assert order.per_item_price == product_version.price
    assert order.num_seats == num_seats
    assert order.b2breceipt_set.count() == 0
    base_url = "http://testserver/"
    receipt_url = f'{urljoin(base_url, reverse("bulk-enrollment-code-receipt"))}?hash={str(order.unique_id)}'
    assert generate_mock.call_count == 1
    assert generate_mock.call_args[0] == ()
    assert generate_mock.call_args[1] == {
        "order": order,
        "receipt_url": receipt_url,
        "cancel_url": urljoin(base_url, reverse("bulk-enrollment-code")),
    }


@pytest.mark.parametrize("key", ["num_seats", "email", "product_version_id"])
def test_create_order_missing_parameters(key, client):
    """
    A 400 error should be returned if one of these parameters is missing
    """
    params = {"num_seats": 123, "email": "a@example.com", "product_version_id": 987}
    resp = client.post(reverse("b2b-checkout"), dict_without_keys(params, key))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {"errors": [f"Missing parameter {key}"]}


def test_create_order_num_seats_integer(client):
    """
    A 400 error should be returned if num_seats is not an integer
    """
    resp = client.post(
        reverse("b2b-checkout"),
        {"num_seats": "nan", "email": "a@example.com", "product_version_id": 987},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {"errors": ["num_seats must be a number"]}


def test_create_order_product_version(client):
    """
    A 404 error should be returned if the product version does not exist
    """
    resp = client.post(
        reverse("b2b-checkout"),
        {"num_seats": 123, "email": "a@example.com", "product_version_id": 987},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_zero_price_checkout(client, mocker):  # pylint:disable=too-many-arguments
    """
    If the order total is $0, we should just fulfill the order and direct the user to our order receipt page
    """
    complete_order_mock = mocker.patch("b2b_ecommerce.views.complete_b2b_order")
    product_version = ProductVersionFactory.create()
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 0,
            "email": "a@email.example.com",
            "product_version_id": product_version.id,
        },
    )
    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    base_url = "http://testserver"
    receipt_url = f'{urljoin(base_url, reverse("bulk-enrollment-code-receipt"))}?hash={str(order.unique_id)}'
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": receipt_url, "method": "GET"}

    assert order.status == B2BOrder.FULFILLED
    assert order.total_price == 0
    assert order.per_item_price == product_version.price
    assert order.b2breceipt_set.count() == 0
    assert order.num_seats == 0
    complete_order_mock.assert_called_once_with(order)


def test_order_fulfilled(client, mocker):  # pylint:disable=too-many-arguments
    """
    Test the happy case
    """
    complete_order_mock = mocker.patch("b2b_ecommerce.views.complete_b2b_order")
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)

    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()

    data["req_reference_number"] = order.reference_number
    data["decision"] = "ACCEPT"

    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = client.post(reverse("b2b-order-fulfillment"), data=data)

    assert len(resp.content) == 0
    assert resp.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == B2BOrder.FULFILLED
    assert order.b2breceipt_set.count() == 1
    assert order.b2breceipt_set.first().data == data

    assert B2BOrderAudit.objects.count() == 1
    order_audit = B2BOrderAudit.objects.last()
    assert order_audit.order == order
    assert dict_without_keys(order_audit.data_after, "updated_on") == dict_without_keys(
        order.to_dict(), "updated_on"
    )
    complete_order_mock.assert_called_once_with(order)


def test_missing_fields(client, mocker):
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
        client.post(reverse("b2b-order-fulfillment"), data=data)
    except KeyError:
        pass

    assert B2BOrder.objects.count() == 0
    assert B2BReceipt.objects.count() == 1
    assert B2BReceipt.objects.first().data == data


@pytest.mark.parametrize("decision", ["CANCEL", "something else"])
def test_not_accept(mocker, client, decision):
    """
    If the decision is not ACCEPT then the order should be marked as failed
    """
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)

    data = {"req_reference_number": order.reference_number, "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = client.post(reverse("b2b-order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.content) == 0
    order.refresh_from_db()
    assert B2BOrder.objects.count() == 1
    assert order.status == B2BOrder.FAILED


def test_ignore_duplicate_cancel(client, mocker):
    """
    If the decision is CANCEL and we already have a duplicate failed order, don't change anything.
    """
    order = B2BOrderFactory.create(status=B2BOrder.FAILED)

    data = {"req_reference_number": order.reference_number, "decision": "CANCEL"}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    resp = client.post(reverse("b2b-order-fulfillment"), data=data)
    assert resp.status_code == status.HTTP_200_OK

    assert B2BOrder.objects.count() == 1
    assert B2BOrder.objects.get(id=order.id).status == B2BOrder.FAILED


@pytest.mark.parametrize(
    "order_status, decision",
    [
        (B2BOrder.FAILED, "ERROR"),
        (B2BOrder.FULFILLED, "ERROR"),
        (B2BOrder.FULFILLED, "SUCCESS"),
    ],
)
def test_error_on_duplicate_order(client, mocker, order_status, decision):
    """If there is a duplicate message (except for CANCEL), raise an exception"""
    order = B2BOrderFactory.create(status=order_status)

    data = {"req_reference_number": order.reference_number, "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    with pytest.raises(EcommerceException) as ex:
        client.post(reverse("b2b-order-fulfillment"), data=data)

    assert B2BOrder.objects.count() == 1
    assert B2BOrder.objects.get(id=order.id).status == order_status

    assert ex.value.args[0] == f"{order} is expected to have status 'created'"


def test_no_permission(client, mocker):
    """
    If the permission class didn't give permission we shouldn't get access to the POST
    """
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=False
    )
    resp = client.post(reverse("b2b-order-fulfillment"), data={})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_order_status(client):
    """
    The order status API should provide information about the order based on its unique_id.
    """
    order = B2BOrderFactory.create()
    resp = client.get(
        reverse("b2b-order-status", kwargs={"hash": str(order.unique_id)})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "email": order.email,
        "num_seats": order.num_seats,
        "product_version": ProductVersionSerializer(
            order.product_version, context={"all_runs": True}
        ).data,
        "item_price": str(order.per_item_price),
        "total_price": str(order.total_price),
        "status": order.status,
    }


def test_order_status_missing(client):
    """
    A 404 should be returned if the hash does not match
    """
    resp = client.get(reverse("b2b-order-status", kwargs={"hash": str(uuid.uuid4())}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_enrollment_codes(client):
    """A CSV file with enrollment codes should be provided for the B2BOrder"""
    coupon_version = CouponVersionFactory.create()
    coupons = [coupon_version.coupon] + [
        CouponVersionFactory.create(
            payment_version=coupon_version.payment_version
        ).coupon
        for _ in range(5)
    ]
    order = B2BOrderFactory.create(
        coupon_payment_version=coupon_version.payment_version
    )

    resp = client.get(reverse("b2b-enrollment-codes", kwargs={"hash": order.unique_id}))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.get("Content-Type") == "text/csv"
    assert (
        resp.get("Content-Disposition")
        == f'attachment; filename="enrollmentcodes-{order.unique_id}.csv"'
    )
    assert sorted(resp.content.decode().split()) == sorted(
        [coupon.coupon_code for coupon in coupons]
    )


def test_enrollment_codes_missing(client):
    """A 404 error should be returned for a missing B2BOrder"""
    resp = client.get(
        reverse("b2b-enrollment-codes", kwargs={"hash": str(uuid.uuid4())})
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
