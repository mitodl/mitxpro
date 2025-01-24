"""Common fixtures"""

import pytest
import responses
from django.test.client import Client
from rest_framework.test import APIClient
from wagtail.models import Site

from users.factories import UserFactory


@pytest.fixture
def user(db):  # noqa: ARG001
    """Creates a user"""
    return UserFactory.create()


@pytest.fixture
def staff_user(db):  # noqa: ARG001
    """Staff user fixture"""
    return UserFactory.create(is_staff=True)


@pytest.fixture
def super_user(db):  # noqa: ARG001
    """Super user fixture"""
    return UserFactory.create(is_staff=True, is_superuser=True)


@pytest.fixture
def user_client(user):
    """Django test client that is authenticated with the user"""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(staff_user):
    """Django test client that is authenticated with the staff user"""
    client = Client()
    client.force_login(staff_user)
    return client


@pytest.fixture
def superuser_client(super_user):
    """Django test client that is authenticated with the superuser"""
    client = Client()
    client.force_login(super_user)
    return client


@pytest.fixture
def user_drf_client(user):
    """DRF API test client that is authenticated with the user"""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_drf_client(admin_user):
    """DRF API test client with admin user"""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def mocked_responses():
    """Mocked responses for requests library"""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_context(mocker, user):
    """Mocked context for serializers"""
    return {"request": mocker.Mock(user=user)}


@pytest.fixture
def wagtail_site():
    """Fixture for Wagtail default site"""
    return Site.objects.get(is_default_site=True)


@pytest.fixture
def home_page(wagtail_site):
    """Fixture for the home page"""
    return wagtail_site.root_page


@pytest.fixture
def valid_address_dict():
    """Yields a dict that will deserialize into a valid legal address"""
    return dict(  # noqa: C408
        first_name="Test",
        last_name="User",
        street_address_1="1 Main St",
        state_or_territory="US-MA",
        city="Cambridge",
        country="US",
        postal_code="02139",
    )


@pytest.fixture
def nplusone_fail(settings):
    """Configures the nplusone app to raise errors"""
    settings.NPLUSONE_RAISE = True


@pytest.fixture
def mock_validate_user_registration(mocker):
    """Fixture to mock validate_user_registration_info method."""
    mock_response = mocker.MagicMock()
    mock_response.name = ""

    mock_client = mocker.MagicMock()
    mock_client.user_validation.validate_user_registration_info.return_value = (
        mock_response
    )
    mocker.patch(
        "courseware.api.get_edx_api_registration_validation_client",
        return_value=mock_client,
    )

    return mock_client
