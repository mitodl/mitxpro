"""Fixtures relevant to the sheets app test suite"""
# pylint: disable=redefined-outer-name
from datetime import datetime
from types import SimpleNamespace
import pytz
import pytest
import factory

from courses.factories import CourseRunFactory, ProgramFactory, ProgramRunFactory
from ecommerce.factories import CompanyFactory, ProductVersionFactory
from sheets.coupon_request_api import CouponRequestRow


@pytest.fixture(autouse=True)
def sheets_settings(settings):
    """Default settings for sheets tests"""
    settings.FEATURES["COUPON_SHEETS"] = True
    settings.SHEETS_REQ_EMAIL_COL = 7
    settings.SHEETS_REQ_PROCESSED_COL = 8
    settings.SHEETS_REQ_ERROR_COL = 9
    settings.SHEETS_REQ_CALCULATED_COLUMNS = {
        settings.SHEETS_REQ_EMAIL_COL,
        settings.SHEETS_REQ_PROCESSED_COL,
        settings.SHEETS_REQ_ERROR_COL,
    }
    _uppercase_a_ord = ord("A")
    settings.SHEETS_REQ_PROCESSED_COL_LETTER = chr(
        settings.SHEETS_REQ_PROCESSED_COL + _uppercase_a_ord
    )
    settings.SHEETS_REQ_ERROR_COL_LETTER = chr(
        settings.SHEETS_REQ_ERROR_COL + _uppercase_a_ord
    )


@pytest.fixture()
def base_data(db):  # pylint: disable=unused-argument
    """Fixture that creates basic objects that are necessary to support a coupon request"""
    company = CompanyFactory.create(name="MIT")
    run = CourseRunFactory.create(courseware_id="course-v1:some-course")
    program = ProgramFactory.create(readable_id="program-v1:some-program")
    program_run = ProgramRunFactory.create(program=program)
    product_objects = [run, program]
    product_versions = ProductVersionFactory.create_batch(
        2,
        text_id=factory.Iterator([obj.text_id for obj in product_objects]),
        product__content_object=factory.Iterator(product_objects),
    )

    return SimpleNamespace(
        company=company,
        run=run,
        program=program,
        program_run=program_run,
        run_product_version=product_versions[0],
        program_product_version=product_versions[1],
    )


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
        "",
        "",
        "",
    ]


@pytest.fixture()
def coupon_req_row(base_data):  # pylint: disable=redefined-outer-name
    """Fixture that returns a valid CouponRequestRow"""
    return CouponRequestRow(
        row_index=2,
        purchase_order_id="purchase_order_id_1",
        coupon_name="mycoupon",
        num_codes=5,
        product_text_id=base_data.run.courseware_id,
        company_name=base_data.company.name,
        activation=datetime(2019, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
        expiration=datetime(2020, 2, 2, 2, 2, 2, tzinfo=pytz.UTC),
        date_processed=False,
        error=None,
        skip_row=False,
        requester="email@example.com",
    )
