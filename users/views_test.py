"""Test for user views"""
import pytest
from django.urls import reverse
from rest_framework import status

from mitxpro.test_utils import drf_datetime


def test_get_user_by_id(user_client, user):
    """Test that user can request their own user by id"""
    resp = user_client.get(reverse("users_api-detail", kwargs={"pk": user.id}))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "is_anonymous": False,
        "is_authenticated": True,
        "created_on": drf_datetime(user.created_on),
        "updated_on": drf_datetime(user.updated_on),
    }


@pytest.mark.parametrize("is_anonymous", [True, False])
def test_get_user_by_me(client, user, is_anonymous):
    """Test that user can request their own user by the 'me' alias"""
    if not is_anonymous:
        client.force_login(user)

    resp = client.get(reverse("users_api-me"))

    assert resp.status_code == status.HTTP_200_OK
    assert (
        resp.json()
        == {"id": None, "username": "", "is_anonymous": True, "is_authenticated": False}
        if is_anonymous
        else {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "is_anonymous": False,
            "is_authenticated": True,
            "created_on": drf_datetime(user.created_on),
            "updated_on": drf_datetime(user.updated_on),
        }
    )
