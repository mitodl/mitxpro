"""
Django app
"""

from django.apps import AppConfig


class RootConfig(AppConfig):
    """AppConfig for this project"""

    name = "mitxpro"

    def ready(self):
        from mitol.common import envs
        from mitol.olposthog.features import configure

        envs.validate()
        configure()
