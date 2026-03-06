"""Tests for mitxpro tasks"""

import uuid
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken

from mitxpro import tasks
from users.factories import UserFactory


def test_clear_expired_tokens(mocker):
    """Test that clear_expired_tokens calls the cleartokens management command"""
    patched_call_command = mocker.patch("mitxpro.tasks.call_command")

    tasks.clear_expired_tokens.delay()
    patched_call_command.assert_called_once_with("cleartokens")


@pytest.mark.django_db
def test_clear_tokens_does_not_delete_unexpired_tokens(settings):
    """Test that cleartokens does not delete tokens that have not yet expired"""
    settings.OAUTH2_PROVIDER = {
        **settings.OAUTH2_PROVIDER,
        "REFRESH_TOKEN_EXPIRE_SECONDS": 60 * 60 * 24 * 30,  # 30 days
    }

    user = UserFactory.create()
    application = Application.objects.create(
        name="test-cleartokens-app",
        client_type="confidential",
        authorization_grant_type="authorization-code",
        skip_authorization=True,
    )

    now = timezone.now()

    # Create an unexpired access token (expires 1 hour from now)
    access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        expires=now + timedelta(hours=1),
        scope="read write",
    )

    # Create a non-revoked refresh token
    refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        access_token=access_token,
    )

    call_command("cleartokens")

    # Unexpired tokens should still exist
    assert AccessToken.objects.filter(pk=access_token.pk).exists()
    assert RefreshToken.objects.filter(pk=refresh_token.pk).exists()


@pytest.mark.django_db
def test_clear_tokens_deletes_expired_tokens(settings):
    """Test that cleartokens deletes tokens that have expired"""
    settings.OAUTH2_PROVIDER = {
        **settings.OAUTH2_PROVIDER,
        "REFRESH_TOKEN_EXPIRE_SECONDS": 60 * 60 * 24 * 30,  # 30 days
    }

    user = UserFactory.create()
    application = Application.objects.create(
        name="test-cleartokens-expired-app",
        client_type="confidential",
        authorization_grant_type="authorization-code",
        skip_authorization=True,
    )

    now = timezone.now()

    # Create an expired access token (expired 60 days ago)
    expired_access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        expires=now - timedelta(days=60),
        scope="read write",
    )

    # Create a revoked refresh token (revoked 60 days ago)
    expired_refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        access_token=expired_access_token,
        revoked=now - timedelta(days=60),
    )

    assert AccessToken.objects.filter(pk=expired_access_token.pk).exists()
    assert RefreshToken.objects.filter(pk=expired_refresh_token.pk).exists()

    call_command("cleartokens")

    # Expired tokens should be deleted
    assert not AccessToken.objects.filter(pk=expired_access_token.pk).exists()
    assert not RefreshToken.objects.filter(pk=expired_refresh_token.pk).exists()
