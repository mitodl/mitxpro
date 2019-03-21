"""tests for admin classes"""
import pytest

from ecommerce.admin import OrderAdmin
from ecommerce.factories import OrderFactory
from ecommerce.models import OrderAudit
from users.factories import UserFactory


pytestmark = pytest.mark.django_db


def test_save_and_log_model(mocker):
    """
    Tests that the save_model() function on OrderAdmin creates an OrderAudit entry
    """
    assert OrderAudit.objects.count() == 0
    order = OrderFactory.create()
    admin = OrderAdmin(model=order, admin_site=mocker.Mock())
    mock_request = mocker.Mock(user=UserFactory.create())
    admin.save_model(
        request=mock_request, obj=admin.model, form=mocker.Mock(), change=mocker.Mock()
    )
    assert OrderAudit.objects.count() == 1
