"""
Tests for signals
"""
import pytest

from courses.factories import CourseFactory, CourseRunFactory
from ecommerce.factories import CouponFactory, CouponEligibilityFactory, ProductFactory
from ecommerce.models import CouponEligibility


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("include_future_runs", [True, False])
def test_apply_coupon_on_all_runs(include_future_runs):
    """
    Test that coupons added to all future course runs of a course,
    only if `include_future_runs = True`
    """

    course = CourseFactory.create()
    run = CourseRunFactory.create(course=course)
    coupon = CouponFactory.create(include_future_runs=include_future_runs)
    product = ProductFactory.create(content_object=run)
    CouponEligibilityFactory.create(coupon=coupon, product=product)

    # create another run with same course
    new_run = CourseRunFactory.create(course=course)
    new_product = ProductFactory.create(content_object=new_run)

    if include_future_runs:
        assert CouponEligibility.objects.filter(
            coupon=coupon, product=new_product
        ).exists()
    else:
        assert not CouponEligibility.objects.filter(
            coupon=coupon, product=new_product
        ).exists()
