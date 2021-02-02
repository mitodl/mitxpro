"""Tests for b2b_ecommerce functions"""
from decimal import Decimal

import faker
import pytest

from b2b_ecommerce.api import (
    complete_b2b_order,
    generate_b2b_cybersource_sa_payload,
    fulfill_b2b_order,
)
from b2b_ecommerce.factories import B2BOrderFactory, B2BCouponFactory
from b2b_ecommerce.models import B2BOrder, B2BOrderAudit
from ecommerce.api import ISO_8601_FORMAT, generate_cybersource_sa_signature
from ecommerce.exceptions import EcommerceException
from ecommerce.factories import CouponPaymentVersionFactory
from ecommerce.models import CouponPaymentVersion
from mitxpro.utils import dict_without_keys, now_in_utc

FAKE = faker.Factory.create()


pytestmark = pytest.mark.django_db


CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY


def test_get_new_b2b_order_by_reference_number():
    """
    get_new_order_by_reference_number returns an Order with status created
    """
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)
    same_order = B2BOrder.objects.get_by_reference_number(order.reference_number)
    assert same_order.id == order.id


@pytest.mark.parametrize("contract_number", [None, "12345"])
@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_signed_payload(mocker, contract_number):
    """
    A valid payload should be signed appropriately
    """
    order = B2BOrderFactory.create(contract_number=contract_number)
    transaction_uuid = "hex"

    now = now_in_utc()
    now_mock = mocker.patch(
        "b2b_ecommerce.api.now_in_utc", autospec=True, return_value=now
    )
    product_version = order.product_version
    product = product_version.product

    mocker.patch(
        "b2b_ecommerce.api.uuid.uuid4",
        autospec=True,
        return_value=mocker.MagicMock(hex=transaction_uuid),
    )
    receipt_url = "https://example.com/base_url/receipt/"
    cancel_url = "https://example.com/base_url/cancel/"
    payload = generate_b2b_cybersource_sa_payload(
        order=order, receipt_url=receipt_url, cancel_url=cancel_url
    )
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    total_price = order.total_price
    assert payload == {
        "access_key": CYBERSOURCE_ACCESS_KEY,
        "amount": str(total_price),
        "currency": "USD",
        "item_0_code": "enrollment_code",
        "item_0_name": f"Enrollment codes for {product_version.description}"[:254],
        "item_0_quantity": order.num_seats,
        "item_0_sku": f"enrollment_code-{str(product.content_type)}-{product.content_object.id}",
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(total_price),
        "line_item_count": 1,
        "locale": "en-us",
        "reference_number": order.reference_number,
        "override_custom_receipt_page": receipt_url,
        "override_custom_cancel_page": cancel_url,
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
        "merchant_defined_data1": order.contract_number or "",
    }
    now_mock.assert_called_once_with()


@pytest.mark.parametrize(
    "contract_number, b2b_coupon_code",
    [
        ("contract_number", "code"),
        ("contract_number", None),
        (None, "code"),
        (None, None),
    ],
)
def test_complete_b2b_order(mocker, contract_number, b2b_coupon_code):
    """
    complete_b2b_order should create the coupons and also send an email for the receipt
    """

    if b2b_coupon_code:
        b2b_coupon = B2BCouponFactory.create(coupon_code=b2b_coupon_code)
    else:
        b2b_coupon = None
    order = B2BOrderFactory.create(contract_number=contract_number, coupon=b2b_coupon)
    payment_version = CouponPaymentVersionFactory.create()
    send_email_mock = mocker.patch("b2b_ecommerce.api.send_b2b_receipt_email")
    create_coupons = mocker.patch(
        "b2b_ecommerce.api.create_coupons", return_value=payment_version
    )

    if b2b_coupon and contract_number:
        expected_name = f"order_{order.id} {contract_number} {b2b_coupon.coupon_code}"
    elif contract_number:
        expected_name = contract_number
    elif b2b_coupon:
        expected_name = b2b_coupon.coupon_code
    else:
        expected_name = f"CouponPayment for order #{order.id}"

    complete_b2b_order(order)
    order.refresh_from_db()
    assert order.coupon_payment_version == payment_version
    create_coupons.assert_called_once_with(
        name=expected_name,
        product_ids=[order.product_version.product.id],
        amount=Decimal("1"),
        num_coupon_codes=order.num_seats,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        payment_type=CouponPaymentVersion.PAYMENT_SALE,
        payment_transaction=order.contract_number or order.reference_number,
    )
    send_email_mock.assert_called_once_with(order)


@pytest.mark.parametrize(
    "order_status, decision",
    [
        (B2BOrder.FAILED, "ERROR"),
        (B2BOrder.FULFILLED, "ERROR"),
        (B2BOrder.FULFILLED, "SUCCESS"),
    ],
)
def test_error_on_duplicate_order(mocker, order_status, decision):
    """If there is a duplicate message (except for CANCEL), raise an exception"""
    order = B2BOrderFactory.create(status=order_status)

    data = {"req_reference_number": order.reference_number, "decision": decision}
    mocker.patch(
        "ecommerce.views.IsSignedByCyberSource.has_permission", return_value=True
    )
    with pytest.raises(EcommerceException) as ex:
        fulfill_b2b_order(data)

    assert B2BOrder.objects.count() == 1
    assert B2BOrder.objects.get(id=order.id).status == order_status

    assert ex.value.args[0] == f"{order} is expected to have status 'created'"


@pytest.mark.parametrize("decision", ["CANCEL", "something else"])
def test_not_accept(decision):
    """
    If the decision is not ACCEPT then the order should be marked as failed
    """
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)

    data = {"req_reference_number": order.reference_number, "decision": decision}
    fulfill_b2b_order(data)
    order.refresh_from_db()
    assert B2BOrder.objects.count() == 1
    assert order.status == B2BOrder.FAILED


def test_ignore_duplicate_cancel():
    """
    If the decision is CANCEL and we already have a duplicate failed order, don't change anything.
    """
    order = B2BOrderFactory.create(status=B2BOrder.FAILED)

    data = {"req_reference_number": order.reference_number, "decision": "CANCEL"}
    fulfill_b2b_order(data)

    assert B2BOrder.objects.count() == 1
    assert B2BOrder.objects.get(id=order.id).status == B2BOrder.FAILED


def test_order_fulfilled(mocker):  # pylint:disable=too-many-arguments
    """
    Test the happy case
    """
    complete_order_mock = mocker.patch("b2b_ecommerce.api.complete_b2b_order")
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)

    data = {}
    for _ in range(5):
        data[FAKE.text()] = FAKE.text()

    data["req_reference_number"] = order.reference_number
    data["decision"] = "ACCEPT"

    fulfill_b2b_order(data)

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
