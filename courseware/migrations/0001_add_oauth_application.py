from urllib.parse import urljoin

from django.db import migrations
from django.conf import settings


def create_edx_oauth_application(apps, schema_editor):
    """Ensures that an Application exists for creating a user in Open edX"""
    from oauth2_provider.models import get_application_model

    Application = get_application_model()
    Application.objects.get_or_create(
        name=settings.OPENEDX_OAUTH_APP_NAME,
        defaults=dict(
            redirect_uris=urljoin(
                settings.OPENEDX_BASE_REDIRECT_URL,
                "/auth/complete/{}/".format(settings.MITXPRO_OAUTH_PROVIDER),
            ),
            client_type="confidential",
            authorization_grant_type="authorization-code",
            skip_authorization=True,
            user=None,
        ),
    )


def remove_edx_oauth_application(apps, schema_editor):
    """Removes an Application for creating a user in Open edX"""
    from oauth2_provider.models import get_application_model

    Application = get_application_model()
    Application.objects.filter(name=settings.OPENEDX_OAUTH_APP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [("oauth2_provider", "0001_initial")]

    operations = [
        migrations.RunPython(create_edx_oauth_application, remove_edx_oauth_application)
    ]
