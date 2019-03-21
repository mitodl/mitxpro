"""Test courseware views"""
import pytest
from django.shortcuts import reverse
from rest_framework import status

pytestmark = [pytest.mark.django_db]


def test_openedx_private_auth_complete_view(client):
    """Verify the openedx_private_auth_complete view returns a 200"""
    response = client.get(reverse("openedx-private-oauth-complete"))
    assert response.status_code == status.HTTP_200_OK
