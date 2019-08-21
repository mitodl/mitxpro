# pylint: disable=redefined-outer-name
"""
Fixtures for voucher tests
"""
from datetime import datetime
from types import SimpleNamespace

import pytest
import pytz
import factory
from django.http import HttpRequest

from faker import Faker
from courses.factories import CourseRunFactory
from ecommerce.factories import (
    CouponEligibilityFactory,
    ProductFactory,
    CouponFactory,
    CouponRedemptionFactory,
    CouponVersionFactory,
    CouponPaymentVersionFactory,
    CompanyFactory,
)
from voucher.factories import VoucherFactory
from voucher.forms import VOUCHER_PARSE_ERROR
from voucher.views import UploadVoucherFormView


fake = Faker()


@pytest.fixture
def upload_voucher_form():
    """
    Mock form to pass in fake cleaned data
    """
    return SimpleNamespace(
        cleaned_data={
            "voucher": {
                "employee_id": fake.password(special_chars=False),
                "voucher_id": fake.password(special_chars=False),
                "course_start_date_input": fake.date_object(),
                "course_id_input": fake.password(),
                "course_title_input": factory.fuzzy.FuzzyText(prefix="Course ").fuzz(),
                "employee_name": fake.name(),
                "pdf": fake.file_name(),
            }
        }
    )


@pytest.fixture
def upload_voucher_form_with_file_field():
    """
    Mock form to pass in a fake file param
    """
    return SimpleNamespace(cleaned_data={"voucher": fake.file_name()})


@pytest.fixture
def upload_voucher_form_with_parse_error():
    """
    Mock form to pass in fake cleaned data
    """
    return SimpleNamespace(errors={"voucher": [VOUCHER_PARSE_ERROR]})


@pytest.fixture
def upload_voucher_form_view(user):
    """
    Returns a mock instance of an UploadVoucherFormView with an attached User
    """
    request = HttpRequest()
    request.user = user
    return UploadVoucherFormView(request=request)


@pytest.fixture
def voucher_and_user(user):
    """
    Returns a voucher and matching user object
    """
    voucher = VoucherFactory(user=user)
    return SimpleNamespace(voucher=voucher, user=user)


@pytest.fixture
def authenticated_client(client, user):
    """
    Returns an authenticated client
    """
    client.force_login(user)
    return client


@pytest.fixture
def voucher_and_user_client(voucher_and_user, client):
    """
    Returns a voucher, user, and authenticated client
    """
    user = voucher_and_user.user
    client.force_login(user)
    return SimpleNamespace(**vars(voucher_and_user), client=client)


@pytest.fixture
def redeemed_voucher_and_user_client(voucher_and_user, client):
    """
    Returns a voucher, user, and authenticated client
    """
    user = voucher_and_user.user
    voucher = voucher_and_user.voucher
    client.force_login(user)
    voucher.coupon = CouponFactory()
    voucher.save()
    CouponRedemptionFactory(coupon_version__coupon=voucher.coupon)
    return SimpleNamespace(**vars(voucher_and_user), client=client)


@pytest.fixture
def voucher_and_partial_matches(voucher_and_user_client):
    """
    Returns a voucher with partial matching CourseRuns
    """
    voucher = voucher_and_user_client.voucher
    company = CompanyFactory()
    course_run_1 = CourseRunFactory(
        start_date=datetime.combine(
            voucher.course_start_date_input, datetime.min.time(), tzinfo=pytz.UTC
        ),
        live=True,
    )
    course_run_2 = CourseRunFactory(
        course__readable_id=voucher.course_id_input, live=True
    )
    course_run_3 = CourseRunFactory(course__title=voucher.course_title_input, live=True)
    course_run_4 = CourseRunFactory(
        course__readable_id=f"{voucher.course_id_input}-noise", live=True
    )
    course_run_5 = CourseRunFactory(
        course__title=f"{voucher.course_title_input}-noise", live=True
    )
    return SimpleNamespace(
        **vars(voucher_and_user_client),
        company=company,
        partial_matches=[
            course_run_1,
            course_run_2,
            course_run_3,
            course_run_4,
            course_run_5,
        ],
    )


@pytest.fixture
def voucher_and_exact_match(voucher_and_user_client):
    """
    Returns a voucher with and an exact matching and partial matching CourseRuns
    """
    voucher = voucher_and_user_client.voucher
    exact_match = CourseRunFactory(
        start_date=datetime.combine(
            voucher.course_start_date_input, datetime.min.time(), tzinfo=pytz.UTC
        ),
        course__readable_id=voucher.course_id_input,
        course__title=voucher.course_title_input,
        live=True,
    )
    return SimpleNamespace(
        **vars(voucher_and_user_client),
        company=CompanyFactory(),
        exact_match=exact_match,
    )


@pytest.fixture
def voucher_and_partial_matches_with_coupons(voucher_and_partial_matches):
    """
    Returns a voucher with partial matching CourseRuns and valid coupons
    """
    context = voucher_and_partial_matches
    products = [
        ProductFactory(content_object=course_run)
        for course_run in context.partial_matches
    ]
    coupon_eligibility_list = [
        CouponEligibilityFactory(product=product) for product in products
    ]
    payment_versions = [
        CouponPaymentVersionFactory(amount=1, company=context.company)
        for _ in coupon_eligibility_list
    ]
    coupon_versions = [
        CouponVersionFactory(
            coupon=coupon_eligibility_list[i].coupon,
            payment_version=payment_versions[i],
        )
        for i in range(len(coupon_eligibility_list))
    ]

    return SimpleNamespace(
        **vars(voucher_and_partial_matches),
        products=products,
        coupon_eligibility_list=coupon_eligibility_list,
        coupon_versions=coupon_versions,
        payment_versions=payment_versions,
    )


@pytest.fixture
def voucher_and_exact_match_with_coupon(voucher_and_exact_match):
    """
    Returns a voucher with exact matching and partial matching CourseRuns and valid coupons
    """
    context = voucher_and_exact_match
    company = context.company
    exact_match = context.exact_match
    product = ProductFactory(content_object=exact_match)
    coupon_eligibility = CouponEligibilityFactory(product=product)
    payment_version = CouponPaymentVersionFactory(amount=1, company=company)
    coupon_version = CouponVersionFactory(
        coupon=coupon_eligibility.coupon, payment_version=payment_version
    )
    return SimpleNamespace(
        **vars(voucher_and_exact_match),
        product=product,
        coupon_eligibility=coupon_eligibility,
        coupon_version=coupon_version,
        payment_version=payment_version,
    )
