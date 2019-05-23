"""
Django app
"""
from django.apps import AppConfig


class RootConfig(AppConfig):
    """AppConfig for this project"""

    name = "mitxpro"

    def ready(self):
        from mitxpro import envs

        envs.validate()
