"""Views for b2b_ecommerce"""

import uuid
from urllib.parse import urlencode, urljoin

import faker
import pytest
from django.urls import reverse
from rest_framework import status

from b2b_ecommerce.factories import (
    B2BCouponFactory,
    B2BOrderFactory,
    ProductVersionFactory,
)
from b2b_ecommerce.models import B2BCoupon, B2BCouponRedemption, B2BOrder, B2BReceipt
from courses.factories import ProgramRunFactory
from ecommerce.factories import CouponVersionFactory
from ecommerce.serializers import FullProductVersionSerializer
from ecommerce.utils import make_checkout_url
from mitxpro.test_utils import assert_drf_json_equal
from mitxpro.utils import dict_without_keys
from users.factories import UserFactory

CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
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
    settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL = CYBERSOURCE_SECURE_ACCEPTANCE_URL
    settings.ECOMMERCE_EMAIL = "ecommerce@example.com"
    settings.EDXORG_BASE_URL = "http://edx_base"


def test_create_order(client, mocker):
    """
    An order is created and a payload
    is generated using generate_b2b_cybersource_sa_payload
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
            "discount_code": "",
            "contract_number": "",
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
    receipt_url = f"{urljoin(base_url, reverse('bulk-enrollment-code-receipt'))}?hash={str(order.unique_id)}"  # noqa: RUF010
    assert generate_mock.call_count == 1
    assert generate_mock.call_args[0] == ()
    assert generate_mock.call_args[1] == {
        "order": order,
        "receipt_url": receipt_url,
        "cancel_url": urljoin(base_url, reverse("bulk-enrollment-code")),
    }


def test_create_order_with_coupon(client, mocker):
    """
    An order is created with a valid coupon
    """
    payload = {"a": "payload"}
    generate_payload_mock = mocker.patch(
        "b2b_ecommerce.views.generate_b2b_cybersource_sa_payload",
        autospec=True,
        return_value=payload,
    )
    product_version = ProductVersionFactory.create()
    coupon = B2BCouponFactory.create(product=product_version.product)
    num_seats = 10
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": num_seats,
            "email": "b@example.com",
            "product_version_id": product_version.id,
            "discount_code": coupon.coupon_code,
            "contract_number": "",
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
    discount = round((product_version.price * num_seats * coupon.discount_percent), 2)
    assert order.discount == discount
    assert order.total_price == ((product_version.price * num_seats) - discount)
    assert order.per_item_price == product_version.price
    assert order.b2bcouponredemption_set.count() == 1
    assert order.b2bcouponredemption_set.first().coupon == coupon
    assert order.num_seats == num_seats
    assert order.b2breceipt_set.count() == 0
    base_url = "http://testserver/"
    receipt_url = f"{urljoin(base_url, reverse('bulk-enrollment-code-receipt'))}?hash={str(order.unique_id)}"  # noqa: RUF010
    assert generate_payload_mock.call_count == 1
    assert generate_payload_mock.call_args[0] == ()
    assert generate_payload_mock.call_args[1] == {
        "order": order,
        "receipt_url": receipt_url,
        "cancel_url": urljoin(base_url, reverse("bulk-enrollment-code")),
    }


def test_create_order_with_invalid_code(client):
    """
    An order is created with an invalid coupon, so a validation error is returned
    """

    product_version = ProductVersionFactory.create()
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 5,
            "email": "b@example.com",
            "product_version_id": product_version.id,
            "discount_code": "nope",
            "contract_number": "",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {"errors": ["Invalid coupon code"]}


@pytest.mark.parametrize("email", ["", "something", "something@", "@something"])
def test_create_order_with_invalid_email(client, email):
    """
    An order is created with an invalid email, so a validation error is returned
    """

    product_version = ProductVersionFactory.create()
    coupon = B2BCouponFactory.create(product=product_version.product)
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 5,
            "email": email,
            "product_version_id": product_version.id,
            "discount_code": coupon.coupon_code,
            "contract_number": "",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {"errors": {"email": "Invalid email"}}


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
        {
            "num_seats": "nan",
            "email": "a@example.com",
            "product_version_id": 987,
            "discount_code": "",
            "contract_number": "",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {"errors": {"num_seats": "num_seats must be a number"}}


def test_create_order_duplicate_reference_number(client):
    """
    A 400 error should be returned if reference_number is duplicate
    """
    duplicate_test_contract_number = "DUPLICATE_TEST"
    B2BOrderFactory.create(
        status=B2BOrder.FULFILLED, contract_number=duplicate_test_contract_number
    )
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 1,
            "email": "a@example.com",
            "product_version_id": 987,
            "discount_code": "",
            "contract_number": duplicate_test_contract_number.lower(),  # additional step for case insensitivity
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {
        "errors": {"contract_number": "This contract number has already been used"}
    }


def test_create_order_product_version(client):
    """
    A 404 error should be returned if the product version does not exist
    """
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": 123,
            "email": "a@example.com",
            "product_version_id": 987,
            "discount_code": "",
            "contract_number": "",
        },
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_zero_price_checkout(client, mocker):
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
            "discount_code": "",
            "contract_number": "",
        },
    )
    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    base_url = "http://testserver"
    receipt_url = f"{urljoin(base_url, reverse('bulk-enrollment-code-receipt'))}?hash={str(order.unique_id)}"  # noqa: RUF010
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": receipt_url, "method": "GET"}

    assert order.status == B2BOrder.FULFILLED
    assert order.total_price == 0
    assert order.per_item_price == product_version.price
    assert order.b2breceipt_set.count() == 0
    assert order.num_seats == 0
    complete_order_mock.assert_called_once_with(order)


def test_order_status(client):
    """
    The order status API should provide information about the order based on its unique_id.
    """
    order = B2BOrderFactory.create()
    resp = client.get(
        reverse("b2b-order-status", kwargs={"hash": str(order.unique_id)})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json(),
        {
            "email": order.email,
            "customer_name": "",
            "num_seats": order.num_seats,
            "product_version": FullProductVersionSerializer(
                order.product_version, context={"all_runs": True}
            ).data,
            "item_price": str(order.per_item_price),
            "total_price": str(order.total_price),
            "status": order.status,
            "discount": None,
            "created_on": order.created_on,
            "reference_number": order.reference_number,
            "coupon_code": order.coupon.coupon_code if order.coupon else None,
            "contract_number": order.contract_number,
            "receipt_data": {"card_type": None, "card_number": None},
        },
    )


def test_order_status_customer_name(client):
    """
    Test that the correct customer name is returned by order status API
    """
    order = B2BOrderFactory.create()
    resp = client.get(
        reverse("b2b-order-status", kwargs={"hash": str(order.unique_id)})
    )

    # Order status API returns no customer name if there is no existing user associated with order email and there is no
    # receipt associated with order
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json().get("customer_name") == ""
    receipt_date = {"req_bill_to_forename": "Test", "req_bill_to_surname": "Name"}

    # Order status API returns customer name from the receipt data when there is no user account with order email

    B2BReceipt.objects.create(order=order, data=receipt_date)
    resp = client.get(
        reverse("b2b-order-status", kwargs={"hash": str(order.unique_id)})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json().get("customer_name") == "Test Name"

    # Order status API returns name of the existing user if there exists an order's email matching user account

    test_user = UserFactory.create(email=order.email)
    resp = client.get(
        reverse("b2b-order-status", kwargs={"hash": str(order.unique_id)})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json().get("customer_name") == test_user.name


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
    rows = [line.split(",") for line in resp.content.decode().split("\r\n")]
    assert rows[0] == [
        "Distribute the links below to each of your learners. Additional instructions are available at:"
    ]
    assert sorted(rows[3 : len(rows) - 1]) == sorted(
        [
            [
                make_checkout_url(
                    code=coupon.coupon_code, product_id=order.product_version.text_id
                )
            ]
            for coupon in coupons
        ]
    )


def test_program_run_enrollment_codes(client):
    """A CSV file with enrollment codes should be provided for the B2BOrder that is attached to a ProgramRun"""
    program_run = ProgramRunFactory()
    coupon_version = CouponVersionFactory.create()
    coupons = [
        coupon_version.coupon,
        CouponVersionFactory.create(
            payment_version=coupon_version.payment_version
        ).coupon,
    ]
    order = B2BOrderFactory.create(
        coupon_payment_version=coupon_version.payment_version, program_run=program_run
    )

    resp = client.get(reverse("b2b-enrollment-codes", kwargs={"hash": order.unique_id}))
    rows = [line.split(",") for line in resp.content.decode().split("\r\n")]
    assert sorted(rows[3 : len(rows) - 1]) == sorted(
        [
            [
                make_checkout_url(
                    code=coupon.coupon_code,
                    product_id=order.product_version.text_id,
                    run_tag=program_run.run_tag,
                )
            ]
            for coupon in coupons
        ]
    )


def test_enrollment_codes_missing(client):
    """A 404 error should be returned for a missing B2BOrder"""
    resp = client.get(
        reverse("b2b-enrollment-codes", kwargs={"hash": str(uuid.uuid4())})
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_coupon_view(client):
    """Information about a coupon should be returned"""
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)
    coupon = B2BCouponFactory.create(product=order.product_version.product)
    B2BCouponRedemption.objects.create(coupon=coupon, order=order)
    response = client.get(
        f"{reverse('b2b-coupon-view')}?"
        f"{urlencode({'code': coupon.coupon_code, 'product_id': order.product_version.product_id})}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "code": coupon.coupon_code,
        "discount_percent": str(coupon.discount_percent),
        "product_id": order.product_version.product_id,
    }


def test_coupon_view_product_with_text_id(client):
    """Information about a coupon should be returned with product text id"""
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)
    coupon = B2BCouponFactory.create(product=order.product_version.product)
    B2BCouponRedemption.objects.create(coupon=coupon, order=order)
    response = client.get(
        f"{reverse('b2b-coupon-view')}?"
        f"{urlencode({'code': coupon.coupon_code, 'product_id': order.product_version.text_id})}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "code": coupon.coupon_code,
        "discount_percent": str(coupon.discount_percent),
        "product_id": order.product_version.product_id,
    }


@pytest.mark.parametrize("reusable", [True, False])
@pytest.mark.parametrize("order_status", [B2BOrder.FULFILLED, B2BOrder.REFUNDED])
def test_reusable_coupon_order_fulfilled(client, reusable, order_status):
    """Information about a reusable coupon should be returned"""
    order = B2BOrderFactory.create(status=order_status)
    coupon = B2BCouponFactory.create(product=None, reusable=reusable)
    B2BCouponRedemption.objects.create(coupon=coupon, order=order)
    response = client.get(
        f"{reverse('b2b-coupon-view')}?"
        f"{urlencode({'code': coupon.coupon_code, 'product_id': order.product_version.product_id})}"
    )

    if reusable:
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "code": coupon.coupon_code,
            "discount_percent": str(coupon.discount_percent),
            "product_id": order.product_version.product_id,
        }
    else:
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_coupon_view_invalid(client, mocker):
    """If a coupon is invalid a 404 response should be returned"""
    patched = mocker.patch.object(
        B2BCoupon.objects, "get_unexpired_coupon", side_effect=B2BCoupon.DoesNotExist
    )
    params = {"code": "x", "product_id": 3}
    response = client.get(f"{reverse('b2b-coupon-view')}?{urlencode(params)}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    patched.assert_called_once_with(
        coupon_code=params["code"], product_id=params["product_id"]
    )


@pytest.mark.parametrize("key", ["code", "product_id"])
def test_coupon_view_missing_param(client, key):
    """Information about a coupon should be returned"""
    params = {"code": "code", "product_id": "product_id"}
    del params[key]
    response = client.get(f"{reverse('b2b-coupon-view')}?{urlencode(params)}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"errors": [f"Missing parameter {key}"]}
