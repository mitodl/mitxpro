"""Users tasks tests"""
# pylint: disable=redefined-outer-name
import json
from unittest.mock import Mock

import pytest
from rest_framework import status

from users.factories import UserFactory
from users.models import User
from users.tasks import (
    make_hubspot_contact_update,
    sync_user_with_hubspot,
    sync_users_batch_with_hubspot,
    hubspot_property_mapping,
    HUBSPOT_API_BASE_URL,
)


@pytest.fixture()
def hubspot_200_response(mocker):
    """Mock a 200 response from Hubspot for successful user update"""
    yield mocker.patch(
        "users.tasks.requests.post", return_value=Mock(status_code=status.HTTP_200_OK)
    )


@pytest.fixture()
def hubspot_202_response(mocker):
    """Mock a 202 response from Hubspot for successful user batch update"""
    yield mocker.patch(
        "users.tasks.requests.post",
        return_value=Mock(status_code=status.HTTP_202_ACCEPTED),
    )


@pytest.mark.django_db
def test_make_hubspot_contact_update():
    """Test that make_hubspot_update creates an appropriate update out of the user"""
    user = UserFactory.create()
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
    sync_user_with_hubspot(None, api_key=None)
    sync_users_batch_with_hubspot(None, api_key=None)


@pytest.mark.django_db
def test_sync_user_with_hubspot(hubspot_200_response):
    """Test syncing a new user with hubspot"""
    user = UserFactory.create()
    sync_user_with_hubspot(user, api_key="key")
    hubspot_200_response.assert_called_once_with(
        data=json.dumps(make_hubspot_contact_update(user)),
        headers={"Content-Type": "application/json"},
        url=f"{HUBSPOT_API_BASE_URL}/contacts/v1/contact/createOrUpdate/email/{user.email}?hapikey=key",
    )


@pytest.mark.django_db
def test_sync_users_batch_with_hubspot(hubspot_202_response):
    """Test syncing a group of users"""
    UserFactory.create()
    UserFactory.create()
    UserFactory.create()

    sync_users_batch_with_hubspot(User.objects.all(), api_key="key")
    hubspot_202_response.assert_called_once_with(
        data=json.dumps(
            [make_hubspot_contact_update(user) for user in User.objects.all()]
        ),
        headers={"Content-Type": "application/json"},
        url=f"{HUBSPOT_API_BASE_URL}/contacts/v1/contact/batch/?hapikey=key",
    )
