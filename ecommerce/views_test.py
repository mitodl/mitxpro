"""ecommerce tests for views"""
import json
from datetime import datetime
from types import SimpleNamespace

import pytz
from django.urls import reverse
import faker
import pytest
import rest_framework.status as status  # pylint: disable=useless-import-alias
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient
import factory

from courses.models import CourseRunEnrollment
from courses.factories import CourseRunFactory
from ecommerce.api import create_unfulfilled_order, make_reference_id
from ecommerce.exceptions import EcommerceException
from ecommerce.factories import (
    CouponEligibilityFactory,
    LineFactory,
    ProductVersionFactory,
    CouponFactory,
    CouponPaymentFactory,
    CouponPaymentVersionFactory,
    CompanyFactory,
)
from ecommerce.models import (
    Basket,
    BasketItem,
    CouponSelection,
    Order,
    OrderAudit,
    Receipt,
    CouponPaymentVersion,
    CourseRunSelection,
    Company,
    CouponEligibility,
    Product,
    DataConsentUser,
)
from ecommerce.serializers import (
    BasketSerializer,
    ProductSerializer,
    CompanySerializer,
    CurrentCouponPaymentSerializer,
)
from mitxpro.test_utils import create_tempfile_csv
from users.factories import UserFactory

CYBERSOURCE_SECURE_ACCEPTANCE_URL = "http://fake"
CYBERSOURCE_REFERENCE_PREFIX = "fake"
CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
FAKE = faker.Factory.create()


pytestmark = pytest.mark.django_db
# pylint: disable=redefined-outer-name,unused-argument,too-many-lines


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


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_zero_price_checkout(
    basket_client,
    mocker,
    basket_and_coupons,
    mock_hubspot_syncs,
    settings,
    hubspot_api_key,
):  # pylint:disable=too-many-arguments
    """
    If the order total is $0, we should just fulfill the order and direct the user to our order receipt page
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
    user = basket_and_coupons.basket_item.basket.user
    order = LineFactory.create(
        order__status=Order.CREATED, product_version__price=0, order__purchaser=user
    ).order
    create_mock = mocker.patch(
        "ecommerce.views.create_unfulfilled_order", autospec=True, return_value=order
    )
    enroll_user_mock = mocker.patch(
        "ecommerce.api.enroll_user_in_order_items", autospec=True
    )
    resp = basket_client.post(reverse("checkout"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"payload": {}, "url": "http://testserver/", "method": "GET"}

    assert create_mock.call_count == 1
    assert create_mock.call_args[0] == (user,)

    assert enroll_user_mock.call_count == 1
    assert enroll_user_mock.call_args[0] == (order,)
    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0
    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_order_fulfilled(
    basket_client,
    mocker,
    basket_and_coupons,
    hubspot_api_key,
    mock_hubspot_syncs,
    settings,
):  # pylint:disable=too-many-arguments
    """
    Test the happy case
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
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
    enroll_user = mocker.patch(
        "ecommerce.api.enroll_user_in_order_items", autospec=True
    )
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

    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0

    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


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


def test_patch_basket_new_item(basket_client, basket_and_coupons):
    """Test that a user can add an item to their basket"""
    data = {"items": [{"id": basket_and_coupons.product_version.product.id}]}
    BasketItem.objects.all().delete()  # clear the basket first
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == render_json(
        BasketSerializer(instance=basket_and_coupons.basket)
    )


def test_patch_basket_multiple_products(basket_client, basket_and_coupons):
    """ Test that an update with multiple products is rejected """
    data = {"items": [{"id": 10}, {"id": 11}]}
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Basket cannot contain more than one item" in resp_data["errors"]["items"]


def test_patch_basket_invalid_coupon_format(basket_client, basket_and_coupons):
    """Test that an update with an invalid format is rejected"""
    resp = basket_client.patch(
        reverse("basket_api"), type="json", data={"coupons": ["coupon code"]}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors") == ["Invalid request"]


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
            "amount": str(basket_and_coupons.coupongroup_worst.payment_version.amount),
            "targets": [basket_and_coupons.product_version.id],
        }
    ]
    assert resp_data.get("items") == original_basket.get("items")
    assert CouponSelection.objects.get(basket=basket).coupon == auto_coupon


def test_patch_basket_clear_coupon_no_auto(basket_client, basket_and_coupons):
    """ Test that all coupons are cleared from basket  """
    basket = basket_and_coupons.basket

    auto_coupon_payment = basket_and_coupons.coupongroup_worst.payment_version
    auto_coupon_payment.automatic = False
    auto_coupon_payment.save()

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

    data = {"items": [{"id": product_version.product.id}]}
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

    data = {"items": [{"id": product_version.product.id}]}
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
    data = {"items": [{"id": product_version.product.id}]}
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
    assert "Invalid product id {}".format(bad_id) in resp_data["errors"]["items"]


@pytest.mark.parametrize("section", ["items", "coupons"])
def test_patch_basket_update_invalid_data(basket_client, basket_and_coupons, section):
    """ Test that invalid product data is rejected with no changes to basket """
    data = dict()
    data[section] = [{"foo": "bar"}]
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    resp_data = resp.json()
    assert "Invalid request" in (
        resp_data["errors"] if section == "coupons" else resp_data["errors"]["items"]
    )


@pytest.mark.parametrize("data", [{"items": [], "coupons": []}, {"items": []}])
def test_patch_basket_clear_product(basket_client, basket_and_coupons, data):
    """ Test that product, coupon, and runs are cleared  """
    resp = basket_client.patch(reverse("basket_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = resp.json()
    assert resp_data.get("coupons") == []
    assert resp_data.get("items") == []
    assert BasketItem.objects.count() == 0
    assert CourseRunSelection.objects.count() == 0


def test_patch_basket_nodata(basket_client, basket_and_coupons):
    """ Test that a patch request with no items or coupons keys is invalidated  """
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
                    "id": product.id,
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
    """A patch request with an run for a different product should result in a 400 error"""
    product_version = basket_and_coupons.product_version
    product = product_version.product
    run = CourseRunFactory.create()
    product.content_object = run.course.program if is_program else run
    product.save()

    # If the product is a course, create a new run on a different course which is invalid.
    # If the product is a program, create a new run on a different program.
    course_run_params = (
        dict(course__program=product.content_object.course.program)
        if not is_program
        else {}
    )
    other_course_run = CourseRunFactory.create(**course_run_params)
    other_run_id = other_course_run.id if is_selected else None

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={"items": [{"id": product.id, "run_ids": [other_run_id]}]},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["errors"] == [
        f"Unable to find run(s) with id(s) {{{other_run_id}}}"
        if is_selected
        else "Each course must have a course run selection"
    ]


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
        data={"items": [{"id": product.id, "run_ids": [run1.id, run2.id]}]},
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
        assert resp.json()["errors"] == ["Only one run per course can be selected"]


def test_patch_basket_already_enrolled(basket_client, basket_and_coupons):
    """A patch request for a run for a course that the user has already enrolled in should result in a 400 error"""
    run = basket_and_coupons.run
    LineFactory.create(order__status=Order.FULFILLED)
    CourseRunEnrollment.objects.create(run=run, user=basket_and_coupons.basket.user)

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={
            "items": [
                {
                    "id": basket_and_coupons.product_version.product.id,
                    "run_ids": [run.id],
                }
            ]
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["errors"] == ["User has already enrolled in run"]


def test_patch_basket__another_user_enrolled(basket_client, basket_and_coupons):
    """A patch request for a run for a course that another user has already enrolled in should succeed"""
    run = basket_and_coupons.run
    order = LineFactory.create(order__status=Order.FULFILLED).order
    CourseRunEnrollment.objects.create(run=run, user=order.purchaser)

    resp = basket_client.patch(
        reverse("basket_api"),
        type="json",
        data={
            "items": [
                {
                    "id": basket_and_coupons.product_version.product.id,
                    "run_ids": [run.id],
                }
            ]
        },
    )
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("as_owner", [True, False])
def test_patch_basket_data_consents(basket_and_agreement, as_owner):
    """ Test that a patch request with DataConsentUser ids updates those objects with consent dates  """
    user = basket_and_agreement.basket.user if as_owner else UserFactory.create()
    client = APIClient()
    client.force_authenticate(user=user)
    consent_user = DataConsentUser.objects.create(
        agreement=basket_and_agreement.agreement,
        user=basket_and_agreement.basket.user,
        coupon=basket_and_agreement.coupon,
    )
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
            tz=pytz.UTC
        ).strftime("%Y-%m-%dT00:00:00Z")
    else:
        assert resp.json()["data_consents"] == []


def test_patch_basket_bad_data_consents(basket_and_agreement):
    """ Test that a patch request with bad DataConsentUser raises a validation error  """
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


def test_post_singleuse_coupons(admin_drf_client, single_use_coupon_json):
    """ Test that the correct model objects are created for a batch of single-use coupons """
    data = single_use_coupon_json
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    model_version = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
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


def test_post_promo_coupon(admin_drf_client, promo_coupon_json):
    """ Test that the correct model objects are created for a promo coupon """
    data = promo_coupon_json
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
        CouponEligibility.objects.filter(product__in=data.get("product_ids")).count()
        == 3
    )


@pytest.mark.parametrize(
    "attribute,bad_value,error",
    [
        [
            "product_ids",
            [9998, 9999],
            "Product with id(s) 9998,9999 could not be found",
        ],
        ["product_ids", [], "At least one product must be selected"],
        ["name", "AlreadyExists", "This field must be unique."],
        ["coupon_code", "AlreadyExists", "This field must be unique."],
    ],
)
def test_create_promo_coupon_bad_product(
    admin_drf_client, promo_coupon_json, attribute, bad_value, error
):
    """ Test that an error is returned if submitted coupon data is invalid  """
    CouponPaymentFactory.create(name="AlreadyExists")
    CouponFactory.create(coupon_code="AlreadyExists")
    data = promo_coupon_json
    data[attribute] = bad_value
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("errors")[0].get(attribute) == error


def test_create_promo_coupon_no_payment_info(admin_drf_client, promo_coupon_json):
    """ Test that a promo CouponPaymentVersion can be created without payment info """
    data = promo_coupon_json
    payment_attrs = ("company", "payment_type", "payment_transaction")
    for attr in payment_attrs:
        data.pop(attr)
    resp = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_200_OK
    cpv = CouponPaymentVersion.objects.get(id=resp.json().get("id"))
    for attr in payment_attrs:
        assert getattr(cpv, attr) is None


def test_create_singleuse_coupon_no_payment_info(
    admin_drf_client, single_use_coupon_json
):
    """ Test that a single-use CouponPaymentVersion cannot be created without payment type, transaction info """
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


def test_create_coupon_permission(user_drf_client, promo_coupon_json):
    """ Test that non-admins cannot create coupons """
    data = promo_coupon_json
    resp = user_drf_client.post(reverse("coupon_api"), type="json", data=data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_coupon_csv_view(admin_client, admin_drf_client, single_use_coupon_json):
    """ Test that a valid csv response is returned for a CouponPaymentVersion """
    data = single_use_coupon_json
    api_response = admin_drf_client.post(reverse("coupon_api"), type="json", data=data)
    cpv = CouponPaymentVersion.objects.get(id=api_response.json().get("id"))
    csv_response = admin_client.get(
        reverse("coupons_csv", kwargs={"version_id": cpv.id})
    )
    assert csv_response.status_code == 200
    assert (
        csv_response.content
        == b"\r\n".join(
            [
                bytes(cv.coupon.coupon_code, encoding="utf8")
                for cv in cpv.couponversion_set.all()
            ]
        )
        + b"\r\n"
    )


def test_coupon_csv_view_forbidden(user_client):
    """ Test that a regular user cannot access a csv download URL """
    response = user_client.get(reverse("coupons_csv", kwargs={"version_id": 1}))
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_coupon_csv_view_404(admin_client):
    """ Test that a 404 is returned for a CouponPaymentVersion that does not exist"""
    response = admin_client.get(reverse("coupons_csv", kwargs={"version_id": 9999}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_products_viewset_list(user_drf_client, coupon_product_ids):
    """ Test that the ProductViewSet returns all products """
    response = user_drf_client.get(reverse("products_api-list"))
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert {product.get("id") for product in products} == set(coupon_product_ids)
    for product in products:
        assert (
            product
            == ProductSerializer(
                instance=Product.objects.get(id=product.get("id"))
            ).data
        )


def test_products_viewset_detail(user_drf_client, coupon_product_ids):
    """ Test that the ProductViewSet returns details for a product """
    response = user_drf_client.get(
        reverse("products_api-detail", kwargs={"pk": coupon_product_ids[0]})
    )
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()
        == ProductSerializer(
            instance=Product.objects.get(id=coupon_product_ids[0])
        ).data
    )


def test_products_viewset_post_forbidden(admin_drf_client):
    """ Test that post requests to the products API viewset is not allowed"""
    response = admin_drf_client.post(reverse("products_api-list"), data={})
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_companies_viewset_list(admin_drf_client):
    """ Test that the CompanyViewSet returns all companies """
    companies = CompanyFactory.create_batch(3)
    response = admin_drf_client.get(reverse("companies_api-list"))
    assert response.status_code == status.HTTP_200_OK
    companies_list = response.json()
    assert {company.get("id") for company in companies_list} == {
        company.id for company in companies
    }
    for company in companies_list:
        assert company == CompanySerializer(instance=company).data


def test_companies_viewset_detail(admin_drf_client):
    """ Test that the CompanyViewSet returns details for a company """
    company = CompanyFactory.create()
    response = admin_drf_client.get(
        reverse("companies_api-detail", kwargs={"pk": company.id})
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == CompanySerializer(instance=company).data


def test_companies_viewset_forbidden():
    """ Test that an anonymous user cannot access the companies list """
    client = APIClient()
    response = client.get(reverse("companies_api-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_companies_viewset_not_staff(user_drf_client):
    """Test that a user who is not staff cannot access the companies list"""
    response = user_drf_client.get(reverse("companies_api-list"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_companies_viewset_post_forbidden(admin_drf_client):
    """ Test that post requests to the companies API viewset is not allowed"""
    response = admin_drf_client.post(reverse("companies_api-list"), data={})
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_bulk_enroll_coupon_list_view(admin_drf_client):
    """ Test that BulkEnrollCouponListView returns CouponEligibility objects"""
    coupons = CouponFactory.create_batch(
        3, enabled=factory.Iterator([True, True, False])
    )
    # Create a 100% coupon
    full_coupon_payment_version = CouponPaymentVersionFactory.create(
        amount=1,
        payment=coupons[0].payment,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    # Create another 100% coupon, then deprecate it with a newer 50% version
    CouponPaymentVersionFactory.create_batch(
        2,
        amount=factory.Iterator([1, 0.5]),
        payment=coupons[1].payment,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    # Create another 100% coupon with a disabled Coupon
    CouponPaymentVersionFactory.create(
        amount=1,
        payment=coupons[2].payment,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    product_coupons = CouponEligibilityFactory.create_batch(
        3, coupon=factory.Iterator(coupons)
    )
    # Apply the full price coupon payment to an additional product
    product_coupons.insert(1, CouponEligibilityFactory.create(coupon=coupons[0]))
    api_url = reverse("bulk_coupons_api")

    response = admin_drf_client.get(api_url)

    assert len(response.data) == 1
    assert len(response.data[0]["products"]) == 2
    assert response.data == [
        {
            **CurrentCouponPaymentSerializer(full_coupon_payment_version.payment).data,
            "products": ProductSerializer(
                [product_coupon.product for product_coupon in product_coupons[0:2]],
                many=True,
            ).data,
        }
    ]


class TestBulkEnrollmentSubmitView:
    """Tests for BulkEnrollmentSubmitView"""

    @pytest.fixture()
    def scenario(self, mocker):
        """Fixtures needed for view test cases"""
        url = reverse("bulk_enroll_submit_api")
        patched_send_emails = mocker.patch("ecommerce.views.send_bulk_enroll_emails")
        patched_available_product_coupons = mocker.patch(
            "ecommerce.views.get_available_bulk_product_coupons"
        )
        emails = ["a@b.com", "c@d.com", "e@f.com"]
        # Make each email into a single-element list to represent a csv with one email per row
        user_csv = create_tempfile_csv([[email] for email in emails])
        return SimpleNamespace(
            patched_send_emails=patched_send_emails,
            patched_available_product_coupons=patched_available_product_coupons,
            emails=emails,
            num_emails=len(emails),
            user_csv=user_csv,
            url=url,
        )

    def test_bulk_enroll_submit_view(self, mocker, admin_drf_client, scenario):
        """Test that BulkEnrollmentSubmitView sends an enrollment email to a set of recipients in a CSV"""
        coupon_payment_version = CouponPaymentVersionFactory.create(
            num_coupon_codes=scenario.num_emails + 1
        )
        available_coupons = CouponEligibilityFactory.create_batch(
            scenario.num_emails + 1
        )
        scenario.patched_available_product_coupons.return_value = mocker.Mock(
            count=mocker.Mock(return_value=len(available_coupons)),
            all=mocker.Mock(return_value=available_coupons),
        )
        product_id = 1
        coupon_payment_id = coupon_payment_version.payment.id

        response = admin_drf_client.post(
            scenario.url,
            data={
                "product_id": product_id,
                "coupon_payment_id": coupon_payment_id,
                "users_file": scenario.user_csv,
            },
            format="multipart",
        )

        assert response.data == {"emails": scenario.emails}
        scenario.patched_available_product_coupons.assert_called_once_with(
            coupon_payment_id, product_id
        )
        scenario.patched_send_emails.assert_called_once_with(
            scenario.emails, available_coupons
        )

    @pytest.mark.parametrize(
        "num_codes,unsent_coupon_count,expected_error",
        [
            [0, 10, "The given coupon has 0 code(s) available"],
            [10, 0, "Only 0 coupon(s) left that have not already been sent to users"],
        ],
    )
    def test_bulk_enroll_submit_view_errors(
        self,
        mocker,
        admin_drf_client,
        scenario,
        num_codes,
        unsent_coupon_count,
        expected_error,
    ):  # pylint: disable=too-many-arguments
        """Test that BulkEnrollmentSubmitView returns errors when not enough product coupons are available"""
        coupon_payment_version = CouponPaymentVersionFactory.create(
            num_coupon_codes=num_codes
        )
        scenario.patched_available_product_coupons.return_value = mocker.Mock(
            count=mocker.Mock(return_value=unsent_coupon_count)
        )
        product_id = 1
        coupon_payment_id = coupon_payment_version.payment.id

        response = admin_drf_client.post(
            scenario.url,
            data={
                "product_id": product_id,
                "coupon_payment_id": coupon_payment_id,
                "users_file": scenario.user_csv,
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        resp_data = response.json()
        assert isinstance(resp_data.get("errors"), list)
        assert expected_error in resp_data["errors"][0]["users_file"]
