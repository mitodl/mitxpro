"""Test permissions"""
import pytest

from mitxpro.permissions import UserIsOwnerPermission


@pytest.mark.parametrize("has_owner_field", [True, False])
@pytest.mark.parametrize("has_perm", [True, False])
def test_user_is_owner_permission(mocker, has_owner_field, has_perm):
    """Tests UserIsOwnerPermission"""
    perm = UserIsOwnerPermission()
    request = mocker.Mock()
    owner = request.user if has_perm else mocker.Mock()
    view = mocker.Mock()
    view.owner_field = "owner" if has_owner_field else None
    obj = mocker.Mock(owner=owner) if has_owner_field else owner

    assert perm.has_object_permission(request, view, obj) is has_perm
