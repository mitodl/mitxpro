"""Users tasks tests"""
import json

import pytest

from users.factories import UserFactory
from users.models import User
from users.tasks import (
    make_hubspot_contact_update,
    sync_user_with_hubspot,
    sync_users_batch_with_hubspot,
    hubspot_property_mapping,
)


def test_make_hubspot_contact_update(user):
    """Test that make_hubspot_update creates an appropriate update out of the user"""
    update = make_hubspot_contact_update(user)
    assert update["email"] == user.email
    for prop in update["properties"]:
        obj, key = hubspot_property_mapping[prop["property"]]
        if obj == "user":
            assert getattr(user, key) == prop["value"]
        elif obj == "profile":
            assert getattr(user.profile, key) == prop["value"]


def test_sync_without_api_key():
    """Test that the sync function return None if HUBSPOT_API_KEY does not have a value"""
    assert sync_user_with_hubspot(None, api_key=None) is None
    assert sync_users_batch_with_hubspot(None, api_key=None) is None


@pytest.mark.django_db
def test_sync_new_user_with_hubspot():
    """Test syncing a new user with hubspot"""
    user = UserFactory.create()
    response = sync_user_with_hubspot(user, api_key="demo")
    assert response is not None
    assert response.status_code == 200
    data = json.loads(response.text)
    assert "vid" in data
    assert data["isNew"]


@pytest.mark.django_db
def test_sync_existing_user_with_hubspot():
    """Test syncing an existing user with hubspot"""
    user = UserFactory.create(email="tester123@hubspot.com")
    response = sync_user_with_hubspot(user, api_key="demo")
    assert response is not None
    assert response.status_code == 200
    data = json.loads(response.text)
    assert "vid" in data
    assert not data["isNew"]


@pytest.mark.django_db
def test_sync_users_batch_with_hubspot():
    """Test syncing a group of users"""
    UserFactory.create()
    UserFactory.create()
    UserFactory.create()

    response = sync_users_batch_with_hubspot(User.objects.all(), api_key="demo")
    assert response is not None
    assert response.status_code == 202
