"""Generates app.json based on settings configuration"""
import json

from django.core.management.base import BaseCommand

from mitxpro import envs


class Command(BaseCommand):
    """Generates app.json based on settings configuration"""

    help = "Generates app.json based on settings configuration"

    def handle(self, *args, **options):
        """Generates app.json based on settings configuration"""
        config = envs.generate_app_json()

        with open("app.json", "w") as app_json:
            app_json.write(json.dumps(config, sort_keys=True, indent=2))
        self.stdout.write(self.style.SUCCESS("Updated app.json"))
