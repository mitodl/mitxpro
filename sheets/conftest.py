"""Fixtures relevant to the sheets app test suite"""
# pylint: disable=redefined-outer-name
from datetime import datetime
from types import SimpleNamespace
import pytz
import pytest

from courses.factories import CourseRunFactory
from ecommerce.factories import CompanyFactory, ProductVersionFactory
from sheets.utils import CouponRequestRow


@pytest.fixture()
def base_data(db):  # pylint: disable=unused-argument
    """Fixture that creates basic objects that are necessary to support a coupon request"""
    company = CompanyFactory.create(name="MIT")
    run = CourseRunFactory.create(courseware_id="course-v1:some-course")
    product_version = ProductVersionFactory.create(
        text_id=run.courseware_id, product__content_object=run
    )
    return SimpleNamespace(company=company, run=run, product_version=product_version)


@pytest.fixture()
def coupon_req_raw_data(base_data):
    """Fixture that returns raw row data that can be parsed as a CouponRequestRow"""
    return [
        "purchase_order_id_1",
        "mycoupon",
        "5",
        base_data.run.courseware_id,
        base_data.company.name,
        "01/01/2019 01:01:01",
        "02/02/2020 02:02:02",
    ]


@pytest.fixture()
def coupon_req_row(base_data):  # pylint: disable=redefined-outer-name
    """Fixture that returns a valid CouponRequestRow"""
    return CouponRequestRow(
        purchase_order_id="purchase_order_id_1",
        coupon_name="mycoupon",
        num_codes=5,
        product_text_id=base_data.run.courseware_id,
        company_name=base_data.company.name,
        activation=datetime(2019, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
        expiration=datetime(2020, 2, 2, 2, 2, 2, tzinfo=pytz.UTC),
        date_processed=False,
    )
