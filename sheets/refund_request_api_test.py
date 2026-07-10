"""Tests for the refund request API"""

import pytest

from courses.factories import (
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramEnrollmentFactory,
    ProgramFactory,
    ProgramRunFactory,
)
from ecommerce.factories import ProductFactory
from sheets.refund_request_api import RefundRequestHandler, RefundRequestRow

pytestmark = pytest.mark.django_db


def _make_refund_row(product_id, order_id, learner_email):
    """Builds a minimal RefundRequestRow for get_order_objects tests"""
    return RefundRequestRow(
        row_index=1,
        response_id=1,
        request_date=None,
        learner_email=learner_email,
        zendesk_ticket_no=None,
        requester_email=None,
        product_id=product_id,
        order_id=order_id,
        order_type=None,
        finance_email=None,
        finance_approve_date=None,
        finance_notes=None,
        refund_processor=None,
        refund_complete_date=None,
        errors=None,
        skip_row=False,
    )


def _build_program_case(run_tag=None, inactive_product=False):
    """
    Program enrollment addressed by its readable id, optionally via a program run id
    (i.e. the readable id plus a run tag suffix like "+R24"). When ``inactive_product``
    is set, an inactive Product is attached to mimic an expired offering.
    """
    program = ProgramFactory.create()
    enrollment = ProgramEnrollmentFactory.create(program=program)
    if inactive_product:
        ProductFactory.create(content_object=program, is_active=False)
    if run_tag:
        program_run = ProgramRunFactory.create(program=program, run_tag=run_tag)
        return program_run.full_readable_id, enrollment
    return program.readable_id, enrollment


def _build_course_run_case():
    """Course run enrollment addressed by a course run readable id"""
    course_run = CourseRunFactory.create()
    enrollment = CourseRunEnrollmentFactory.create(run=course_run)
    return course_run.courseware_id, enrollment


@pytest.mark.parametrize(
    "build_case",
    [
        pytest.param(lambda: _build_program_case(run_tag="R24"), id="program_run_id"),
        pytest.param(lambda: _build_program_case(), id="program_id"),
        pytest.param(_build_course_run_case, id="course_run_id"),
        pytest.param(
            lambda: _build_program_case(run_tag="R24", inactive_product=True),
            id="program_run_id_inactive_product",
        ),
    ],
)
def test_get_order_objects_resolves_enrollment(build_case):
    """
    get_order_objects should resolve the order and enrollment for any product id shape,
    including a program run id whose run tag suffix isn't part of the Program's readable id,
    and even when the product is inactive (e.g. an expired offering being refunded).
    """
    product_id, enrollment = build_case()

    row = _make_refund_row(
        product_id=product_id,
        order_id=enrollment.order.id,
        learner_email=enrollment.order.purchaser.email,
    )

    order, resolved_enrollment = RefundRequestHandler.get_order_objects(row)
    assert order == enrollment.order
    assert resolved_enrollment == enrollment
