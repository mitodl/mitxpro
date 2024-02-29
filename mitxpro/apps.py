"""
Django app
"""
from django.apps import AppConfig


class RootConfig(AppConfig):
    """AppConfig for this project"""

    name = "mitxpro"

    def ready(self):  # noqa: D102
        from mitol.common import envs

        envs.validate()
