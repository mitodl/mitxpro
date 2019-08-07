"""Views for b2b_ecommerce"""
from urllib.parse import urljoin

from django.urls import reverse
import faker
import pytest
from rest_framework import status

from b2b_ecommerce.factories import B2BOrderFactory, ProductVersionFactory
from b2b_ecommerce.models import B2BOrder, B2BOrderAudit, B2BReceipt
from ecommerce.exceptions import EcommerceException
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
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 10,
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

    base_url = "http://testserver/"
    receipt_url = urljoin(base_url, reverse("bulk-enrollment-code-receipt"))
    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    assert generate_mock.call_count == 1
    assert generate_mock.call_args[0] == ()
    assert generate_mock.call_args[1] == {
        "order": order,
        "receipt_url": receipt_url,
        "cancel_url": base_url,
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


def test_zero_price_checkout(client):  # pylint:disable=too-many-arguments
    """
    If the order total is $0, we should just fulfill the order and direct the user to our order receipt page
    """
    product_version = ProductVersionFactory.create()
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 0,
            "email": "a@email.example.com",
            "product_version_id": product_version.id,
        },
    )
    base_url = "http://testserver"
    receipt_url = urljoin(base_url, reverse("bulk-enrollment-code-receipt"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": receipt_url, "method": "GET"}

    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    assert order.status == B2BOrder.FULFILLED
    assert order.total_price == 0
    assert order.per_item_price == 0
    assert order.b2breceipt_set.count() == 0
    assert order.num_seats == 0


def test_order_fulfilled(client, mocker):  # pylint:disable=too-many-arguments
    """
    Test the happy case
    """
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

    assert ex.value.args[0] == "Order {id} is expected to have status 'created'".format(
        id=order.id
    )


def test_no_permission(client, mocker):
    """
    If the permission class didn't give permission we shouldn't get access to the POST
    """
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=False
    )
    resp = client.post(reverse("b2b-order-fulfillment"), data={})
    assert resp.status_code == status.HTTP_403_FORBIDDEN
