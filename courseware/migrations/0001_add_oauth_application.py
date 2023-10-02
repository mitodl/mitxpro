from urllib.parse import urljoin

from django.conf import settings
from django.db import migrations


def create_edx_oauth_application(apps, schema_editor):  # noqa: ARG001
    """Ensures that an Application exists for creating a user in Open edX"""  # noqa: D401, E501
    from oauth2_provider.models import get_application_model

    Application = get_application_model()
    Application.objects.get_or_create(
        name=settings.OPENEDX_OAUTH_APP_NAME,
        defaults={
            "redirect_uris": urljoin(
                settings.OPENEDX_BASE_REDIRECT_URL,
                f"/auth/complete/{settings.MITXPRO_OAUTH_PROVIDER}/",
            ),
            "client_type": "confidential",
            "authorization_grant_type": "authorization-code",
            "skip_authorization": True,
            "user": None,
        },
    )


def remove_edx_oauth_application(apps, schema_editor):  # noqa: ARG001
    """Removes an Application for creating a user in Open edX"""  # noqa: D401
    from oauth2_provider.models import get_application_model

    Application = get_application_model()
    Application.objects.filter(name=settings.OPENEDX_OAUTH_APP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [("oauth2_provider", "0001_initial")]

    operations = [
        migrations.RunPython(create_edx_oauth_application, remove_edx_oauth_application)
    ]
