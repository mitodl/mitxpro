"""Tests for admin interface for b2b_ecommerce"""
import pytest

from b2b_ecommerce.admin import B2BCouponAdmin, B2BOrderAdmin
from b2b_ecommerce.factories import B2BCouponFactory, B2BOrderFactory
from b2b_ecommerce.models import B2BOrderAudit, B2BCouponAudit


pytestmark = pytest.mark.django_db


def test_save_and_log_order(mocker):
    """
    Tests that the save_model() function on B2BOrderAdmin creates an B2BOrderAudit entry
    """
    assert B2BOrderAudit.objects.count() == 0
    order = B2BOrderFactory.create()
    admin = B2BOrderAdmin(model=order, admin_site=mocker.Mock())
    admin.save_model(
        request=mocker.Mock(user=None),
        obj=admin.model,
        form=mocker.Mock(),
        change=mocker.Mock(),
    )
    assert B2BOrderAudit.objects.count() == 1


def test_save_and_log_coupon(mocker):
    """Tests that the save_model() function on B2BOrderAdmin creates an B2BOrderAudit entry"""
    assert B2BCouponAudit.objects.count() == 0
    coupon = B2BCouponFactory.create()
    admin = B2BCouponAdmin(model=coupon, admin_site=mocker.Mock())
    admin.save_model(
        request=mocker.Mock(user=None),
        obj=admin.model,
        form=mocker.Mock(),
        change=mocker.Mock(),
    )
    assert B2BCouponAudit.objects.count() == 1
