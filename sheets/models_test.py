"""Tests for sheets models"""
import pytest

from django.core.exceptions import ValidationError

from sheets.factories import GoogleApiAuthFactory


@pytest.mark.django_db
def test_google_api_auth_singleton():
    """
    An error should be raised if there is an attempt to create a GoogleApiAuth object
    when one already exists
    """
    GoogleApiAuthFactory.create()
    with pytest.raises(ValidationError):
        GoogleApiAuthFactory.create()
