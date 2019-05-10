"""Ecommerce mail API tests"""
import pytest

from ecommerce.factories import (
    CouponPaymentVersionFactory,
    CouponEligibilityFactory,
    CompanyFactory,
)
from ecommerce.mail_api import send_bulk_enroll_emails
from mail.constants import EMAIL_BULK_ENROLL

lazy = pytest.lazy_fixture


@pytest.mark.django_db
@pytest.fixture()
def company():
    """Company object fixture"""
    return CompanyFactory.create(name="MIT")


@pytest.mark.django_db
@pytest.mark.parametrize("test_company", [lazy("company"), None])
def test_send_bulk_enroll_emails(mocker, settings, test_company):
    """
    send_bulk_enroll_emails should build messages for each recipient and send them
    """
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")

    settings.SITE_BASE_URL = "http://test.com/"
    email = "a@b.com"
    payment_version = CouponPaymentVersionFactory.create(company=test_company)
    product_coupon = CouponEligibilityFactory.create(
        coupon__payment=payment_version.payment
    )

    expected_qs = "product={}&code={}".format(
        product_coupon.product.id, product_coupon.coupon.coupon_code
    )
    expected_context = {
        "enrollable_title": product_coupon.product.content_object.title,
        "enrollment_url": "http://test.com/enroll/?{}".format(expected_qs),
        "company_name": test_company.name if test_company else None,
    }

    send_bulk_enroll_emails([email], [product_coupon])

    patched_mail_api.build_user_specific_messages.assert_called_once()
    assert (
        patched_mail_api.build_user_specific_messages.call_args[0][0]
        == EMAIL_BULK_ENROLL
    )
    assert list(patched_mail_api.build_user_specific_messages.call_args[0][1]) == [
        (email, expected_context)
    ]

    patched_mail_api.send_messages.assert_called_once_with(
        patched_mail_api.build_user_specific_messages.return_value
    )
