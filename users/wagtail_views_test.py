"""Tests for users Wagtail admin views"""

import pytest
from unittest.mock import patch

from wagtail.users.views.users import IndexView as WagtailUserIndexView

from users.factories import UserFactory
from users.models import User
from users.wagtail_views import UserIndexView, UserViewSet

pytestmark = pytest.mark.django_db


class TestUserIndexViewOrderQueryset:
    """Tests for UserIndexView.order_queryset"""

    def _make_view(self, ordering):
        view = UserIndexView()
        view.ordering = ordering
        view.model = User
        return view

    def test_order_by_name_ascending(self):
        """ordering='name' sorts by name ascending"""
        UserFactory(name="Zebra")
        UserFactory(name="Alpha")
        view = self._make_view("name")
        result = list(
            view.order_queryset(User.objects.all()).values_list("name", flat=True)
        )
        assert result == sorted(result)

    def test_order_by_name_descending(self):
        """ordering='-name' sorts by name descending"""
        UserFactory(name="Zebra")
        UserFactory(name="Alpha")
        view = self._make_view("-name")
        result = list(
            view.order_queryset(User.objects.all()).values_list("name", flat=True)
        )
        assert result == sorted(result, reverse=True)

    @pytest.mark.parametrize("ordering", ["name", "-name"])
    def test_name_ordering_does_not_reference_last_name(self, ordering):
        """name/−name ordering must not raise FieldError for last_name"""
        UserFactory.create_batch(3)
        view = self._make_view(ordering)
        # Evaluating the queryset would raise FieldError if last_name is used
        list(view.order_queryset(User.objects.all()))

    def test_unknown_ordering_delegates_to_super(self):
        """Unrecognised ordering falls through to Wagtail's default implementation"""
        view = self._make_view("email")
        qs = User.objects.all()
        with patch.object(
            WagtailUserIndexView, "order_queryset", return_value=qs
        ) as mock_super:
            result = view.order_queryset(qs)
            mock_super.assert_called_once()
        assert result is qs


class TestUserViewSet:
    """Tests for UserViewSet"""

    def test_index_view_class_is_custom(self):
        """UserViewSet must use the custom UserIndexView"""
        assert UserViewSet.index_view_class is UserIndexView
