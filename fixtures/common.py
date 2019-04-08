"""Common fixtures"""
# pylint: disable=unused-argument, redefined-outer-name

import pytest
from django.test.client import Client
from rest_framework.test import APIClient

from users.factories import UserFactory


@pytest.fixture
def user(db):
    """Creates a user"""
    return UserFactory.create()


@pytest.fixture
def user_client(user):
    """Django test client that is authenticated with the user"""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(user):
    """Django test client that is authenticated with an admin user"""
    client = Client()
    client.force_login(UserFactory.create(is_staff=True))
    return client


@pytest.fixture
def user_drf_client(user):
    """DRF API test client that is authenticated with the user"""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_drf_client():
    """ DRF API test client with admin user """
    client = APIClient()
    client.force_authenticate(user=UserFactory.create(is_staff=True))
    return client
