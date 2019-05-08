"""Test for user views"""
import pytest
from django.urls import reverse
from rest_framework import status

from mitxpro.test_utils import drf_datetime


@pytest.mark.django_db
def test_cannot_create_user(client):
    """Verify the api to create a user is nonexistent"""
    resp = client.post("/api/users/", data={"name": "Name"})

    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_update_user(user_client, user):
    """Verify the api to update a user is doesn't accept the verb"""
    resp = user_client.patch(
        reverse("users_api-detail", kwargs={"pk": user.id}), data={"name": "Name"}
    )

    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_get_user_by_id(user_client, user):
    """Test that user can request their own user by id"""
    resp = user_client.get(reverse("users_api-detail", kwargs={"pk": user.id}))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "id": user.id,
        "username": user.username,
        "name": user.name,
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
        == {
            "id": None,
            "username": "",
            "email": None,
            "legal_address": None,
            "is_anonymous": True,
            "is_authenticated": False,
        }
        if is_anonymous
        else {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "legal_address": {
                "first_name": user.legal_address.first_name,
                "last_name": user.legal_address.last_name,
                "street_address": [user.legal_address.street_address_1],
                "city": user.legal_address.city,
                "state_or_territory": user.legal_address.state_or_territory,
                "country": user.legal_address.country,
                "postal_code": user.legal_address.postal_code,
            },
            "is_anonymous": False,
            "is_authenticated": True,
            "created_on": drf_datetime(user.created_on),
            "updated_on": drf_datetime(user.updated_on),
        }
    )


@pytest.mark.django_db
def test_countries_states_view(client):
    """Test that a list of countries and states is returned"""
    resp = client.get(reverse("countries_api-list"))
    countries = {country["code"]: country for country in resp.json()}
    assert len(countries.get("US").get("states")) > 50
    assert {"code": "CA-QC", "name": "Quebec"} in countries.get("CA").get("states")
    assert len(countries.get("FR").get("states")) == 0
    assert countries.get("US").get("name") == "United States"
    assert countries.get("TW").get("name") == "Taiwan"
