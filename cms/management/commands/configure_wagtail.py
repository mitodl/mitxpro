"""Management command to fully configure Wagtail"""
from django.core.management.base import BaseCommand

from cms.api import configure_wagtail


class Command(BaseCommand):
    """Ensures that all appropriate changes have been made to Wagtail that will make the site navigable."""

    help = __doc__

    def handle(self, *args, **options):
        configure_wagtail()
