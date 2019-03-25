"""Courseware API functions"""
from datetime import datetime, timedelta
from urllib.parse import urljoin
import pytz
import requests
from rest_framework import status

from django.conf import settings
from oauth2_provider.models import Application, AccessToken
from oauthlib.common import generate_token

from courseware.models import CoursewareUser
from courseware.constants import PLATFORM_EDX


OPENEDX_REGISTER_USER_PATH = "/user_api/v1/account/registration/"
OPENEDX_REQUEST_DEFAULTS = dict(country="US", honor_code=True)


def create_edx_user(user):
    """Makes a request to create an equivalent user in Open edX"""
    application = Application.objects.get(name=settings.OPENEDX_OAUTH_APP_NAME)
    expiry_date = datetime.now(tz=pytz.utc) + timedelta(
        hours=settings.OPENEDX_TOKEN_EXPIRES_HOURS
    )
    access_token, _ = AccessToken.objects.update_or_create(
        user=user,
        application=application,
        defaults=dict(token=generate_token(), expires=expiry_date),
    )

    resp = requests.post(
        urljoin(settings.OPENEDX_API_BASE_URL, OPENEDX_REGISTER_USER_PATH),
        data=dict(
            username=user.username,
            email=user.email,
            name=user.name,
            provider=settings.MITXPRO_OAUTH_PROVIDER,
            access_token=access_token.token,
            **OPENEDX_REQUEST_DEFAULTS,
        ),
    )
    # edX responds with 200 on success, not 201
    if resp.status_code == status.HTTP_200_OK:
        CoursewareUser.objects.create(
            user=user, platform=PLATFORM_EDX, has_been_synced=True
        )
    return resp
