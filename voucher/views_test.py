# pylint: disable=unused-import
"""
Test voucher views.py
"""
import json
from urllib.parse import urljoin

from django.urls import reverse
import pytest

from ecommerce.factories import CouponVersionFactory, CouponEligibilityFactory
from users.factories import UserFactory
from voucher.factories import VoucherFactory
from voucher.models import Voucher

# pylint: disable=redefined-outer-name

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def mock_logger(mocker):
    """ Mock the log """
    yield mocker.patch("voucher.views.log")


def test_anonymous_user_permissions(client):
    """
    Verify an anonymous user cannot access the voucher pages
    """
    assert client.get(reverse("voucher:upload")).status_code == 302
    assert client.get(reverse("voucher:enroll")).status_code == 302
    assert client.get(reverse("voucher:resubmit")).status_code == 302
    assert client.get(reverse("voucher:redeemed")).status_code == 302


def test_authenticated_user_permissions(authenticated_client):
    """
    Verify an authenticated user can access the voucher pages
    """
    assert authenticated_client.get(reverse("voucher:upload")).status_code == 200
    assert authenticated_client.get(reverse("voucher:resubmit")).status_code == 200
    assert authenticated_client.get(reverse("voucher:redeemed")).status_code == 200


def test_upload_voucher_form_view_voucher_create(
    upload_voucher_form_view, upload_voucher_form
):
    """
    Test UploadVoucherFormView POST creates a voucher if one doesn't already exist matching the given voucher values
    """
    response = upload_voucher_form_view.form_valid(upload_voucher_form)
    assert response.status_code == 302
    assert response.url == reverse("voucher:enroll")
    assert response.url.startswith("/boeing")
    assert (
        Voucher.objects.filter(**upload_voucher_form.cleaned_data["voucher"]).count()
        == 1
    )


def test_upload_voucher_form_view_parse_error(
    mock_logger, upload_voucher_form_view, upload_voucher_form_with_parse_error
):
    """
    Test UploadVoucherFormView POST redirects to resubmit if there is a parsing error
    """
    response = upload_voucher_form_view.form_invalid(
        upload_voucher_form_with_parse_error
    )
    assert response.status_code == 302
    assert response.url == reverse("voucher:resubmit")
    assert response.url.startswith("/boeing")
    username = upload_voucher_form_view.request.user.username
    mock_logger.error.assert_any_call(
        "Voucher uploaded by %s could not be parsed", username
    )


def test_upload_voucher_form_view_voucher_update(
    upload_voucher_form_view, upload_voucher_form
):
    """
    Test UploadVoucherFormView POST retrieves a voucher if one already exists matching the given voucher values
    """
    values = upload_voucher_form.cleaned_data["voucher"]
    values["pdf"] = "/vouchers/another_name.pdf"
    voucher = Voucher.objects.create(
        **values, user=upload_voucher_form_view.request.user
    )
    response = upload_voucher_form_view.form_valid(upload_voucher_form)
    assert response.status_code == 302
    assert response.url == reverse("voucher:enroll")

    values.pop("pdf")
    assert Voucher.objects.filter(**values).count() == 1
    assert Voucher.objects.get(**values).uploaded > voucher.uploaded


def test_upload_voucher_form_view_voucher_other_user(
    mock_logger, upload_voucher_form_view, upload_voucher_form
):
    """
    Test UploadVoucherFormView POST does not allow an upload of the same voucher from another user
    """
    values = upload_voucher_form.cleaned_data["voucher"]
    new_user = UserFactory.create()
    voucher = Voucher.objects.create(**values, user=new_user)
    response = upload_voucher_form_view.form_valid(upload_voucher_form)
    assert response.status_code == 302
    assert response.url == reverse("voucher:resubmit")

    values.pop("pdf")
    assert Voucher.objects.filter(**values).count() == 1
    assert Voucher.objects.get(**values).uploaded == voucher.uploaded
    mock_logger.error.assert_called_once_with(
        "%s uploaded a voucher previously uploaded by %s",
        upload_voucher_form_view.request.user.username,
        new_user.username,
    )


def test_get_enroll_view_with_no_voucher(authenticated_client):
    """
    Test the EnrollView GET method when there is no current voucher for the user
    """
    response = authenticated_client.get(reverse("voucher:enroll"))
    assert response.status_code == 302
    assert response.url == reverse("voucher:upload")
    assert response.url.startswith("/boeing")


def test_get_enroll_view_with_redeemed_voucher(redeemed_voucher_and_user_client):
    """
    Test the EnrollView GET method when the current voucher is redeemed
    """
    client = redeemed_voucher_and_user_client.client
    response = client.get(reverse("voucher:enroll"))
    assert response.status_code == 302
    assert response.url == reverse("voucher:redeemed")


def test_get_enroll_view_with_no_matches(voucher_and_user_client):
    """
    Test the EnrollView GET method when there are no course run matches
    """
    client = voucher_and_user_client.client
    response = client.get(reverse("voucher:enroll"))
    assert response.status_code == 302
    assert response.url == reverse("voucher:resubmit")


def test_get_enroll_view_with_matches(
    voucher_and_partial_matches_with_coupons, settings
):
    """
    Test the EnrollView GET method when there are course run matches
    """
    context = voucher_and_partial_matches_with_coupons
    client = context.client
    settings.VOUCHER_COMPANY_ID = context.company.id
    response = client.get(reverse("voucher:enroll"))
    assert response.status_code == 200

    product_ids = [product.id for product in context.products]
    coupon_ids = [
        coupon_version.coupon.id for coupon_version in context.coupon_versions
    ]
    titles = [
        "{title} - starts {start_date}".format(
            title=match.title, start_date=match.start_date.strftime("%b %d, %Y")
        )
        for match in context.partial_matches
    ]
    for coupon_choice in response.context[0]["eligible_choices"]:
        product_id, coupon_id = json.loads(coupon_choice[0])
        assert product_id in product_ids
        assert coupon_id in coupon_ids
        assert coupon_choice[1] in titles


def test_post_enroll_view_with_coupon_choice(
    voucher_and_exact_match_with_coupon, settings
):
    """
    Test the EnrollView POST method with a valid coupon choice
    """
    context = voucher_and_exact_match_with_coupon
    client = context.client
    voucher = context.voucher
    coupon_version = context.coupon_version
    product = context.product
    response = client.post(
        reverse("voucher:enroll"),
        {"coupon_version": json.dumps((product.id, coupon_version.coupon.id))},
    )
    assert response.status_code == 302
    assert response.url == (
        f"{urljoin(settings.SITE_BASE_URL, reverse('checkout-page'))}?"
        f"product={product.id}&code={coupon_version.coupon.coupon_code}"
    )
    assert Voucher.objects.get(id=voucher.id).coupon == coupon_version.coupon


def test_post_enroll_view_without_coupon_choice(
    voucher_and_exact_match_with_coupon, settings
):
    """
    Test the EnrollView POST method with a valid coupon choice
    """
    context = voucher_and_exact_match_with_coupon
    client = context.client
    settings.VOUCHER_COMPANY_ID = context.company.id
    response = client.post(reverse("voucher:enroll"), {"coupon_version": ""})
    assert response.status_code == 200
    assert b"Coupon Version is required." in response.content


def test_post_enroll_view_with_empty_coupon_choice(
    voucher_and_exact_match_with_coupon, settings
):
    """
    Test the EnrollView POST method with a valid coupon choice
    """
    context = voucher_and_exact_match_with_coupon
    client = context.client
    settings.VOUCHER_COMPANY_ID = context.company.id
    response = client.post(reverse("voucher:enroll"), {"coupon_version": ("", "")})
    assert response.status_code == 200
    assert b"Coupon Version is required." in response.content


def test_post_enroll_view_with_stolen_only_coupon(
    mock_logger, voucher_and_exact_match_with_coupon, settings
):
    """
    Test the EnrollView POST logs an error if the coupon is stolen and there aren't any more
    """
    context = voucher_and_exact_match_with_coupon
    settings.VOUCHER_COMPANY_ID = context.company.id
    client = context.client
    coupon_version = context.coupon_version

    # Create a voucher and steal the last coupon
    VoucherFactory(coupon=coupon_version.coupon)
    product = context.product
    response = client.post(
        reverse("voucher:enroll"),
        {"coupon_version": json.dumps((product.id, coupon_version.coupon.id))},
    )
    assert response.status_code == 302
    assert response.url == reverse("voucher:resubmit")
    mock_logger.error.assert_called_once_with(
        "Found no valid coupons for matches for voucher %s", context.voucher.id
    )


def test_post_enroll_view_with_stolen_coupon(
    voucher_and_exact_match_with_coupon, settings
):
    """
    Test the EnrollView POST method recovers a second coupon code if the first is stolen
    """
    context = voucher_and_exact_match_with_coupon
    settings.VOUCHER_COMPANY_ID = context.company.id
    client = context.client
    voucher = context.voucher
    coupon_version1 = context.coupon_version

    # Create a voucher and steal the coupon
    VoucherFactory(coupon=coupon_version1.coupon)

    # Create a second valid coupon
    coupon_eligibility = CouponEligibilityFactory(product=context.product)
    coupon_version2 = CouponVersionFactory(
        coupon=coupon_eligibility.coupon, payment_version=context.payment_version
    )
    product = context.product
    response = client.post(
        reverse("voucher:enroll"),
        {"coupon_version": json.dumps((product.id, coupon_version1.coupon.id))},
    )
    assert response.status_code == 302
    assert response.url == (
        f"{urljoin(settings.SITE_BASE_URL, reverse('checkout-page'))}?"
        f"product={product.id}&code={coupon_version2.coupon.coupon_code}"
    )
    assert Voucher.objects.get(id=voucher.id).coupon == coupon_version2.coupon
