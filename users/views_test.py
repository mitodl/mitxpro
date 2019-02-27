"""Test for user views"""
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
        "created_on": drf_datetime(user.created_on),
        "updated_on": drf_datetime(user.updated_on),
    }


def test_get_user_by_me(user_client, user):
    """Test that user can request their own user by the 'me' alias"""
    resp = user_client.get(reverse("users_api-detail", kwargs={"pk": "me"}))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "created_on": drf_datetime(user.created_on),
        "updated_on": drf_datetime(user.updated_on),
    }
