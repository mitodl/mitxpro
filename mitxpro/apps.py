"""
Django app
"""
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class RootConfig(AppConfig):
    """AppConfig for this project"""

    name = "mitxpro"

    def ready(self):
        missing_settings = [
            setting_name
            for setting_name in settings.MANDATORY_SETTINGS
            if getattr(settings, setting_name, None) in (None, "")
        ]

        if missing_settings:
            raise ImproperlyConfigured(
                "The following settings are missing: {}".format(
                    ", ".join(missing_settings)
                )
            )
