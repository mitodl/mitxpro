"""Tests for mitxpro tasks"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken

from mitxpro import tasks
from users.factories import UserFactory


def test_clear_expired_tokens(mocker):
    """Test that clear_expired_tokens calls the clear_expired function"""
    patched_clear_expired = mocker.patch("mitxpro.tasks.clear_expired")

    tasks.clear_expired_tokens.delay()
    patched_clear_expired.assert_called_once_with()


@pytest.mark.parametrize(
    ("token_expires_delta", "token_revoked_delta", "expect_deleted"),
    [
        pytest.param(timedelta(hours=1), None, False, id="unexpired"),
        pytest.param(timedelta(days=-60), timedelta(days=-60), True, id="expired"),
        pytest.param(
            timedelta(hours=1),
            timedelta(hours=1),
            False,
            id="unexpired-with-future-revoked",
        ),
        pytest.param(timedelta(days=-60), None, True, id="expired-not-revoked"),
    ],
)
@pytest.mark.django_db
def test_clear_expired_tokens_deletes_correctly(
    settings, token_expires_delta, token_revoked_delta, expect_deleted
):
    """Test that clear_expired_tokens deletes expired tokens and preserves unexpired ones"""
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

    access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        expires=now + token_expires_delta,
        scope="read write",
    )

    refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=uuid.uuid4().hex,
        access_token=access_token,
        **({"revoked": now + token_revoked_delta} if token_revoked_delta else {}),
    )

    tasks.clear_expired_tokens()

    assert AccessToken.objects.filter(pk=access_token.pk).exists() == (
        not expect_deleted
    )
    assert RefreshToken.objects.filter(pk=refresh_token.pk).exists() == (
        not expect_deleted
    )
