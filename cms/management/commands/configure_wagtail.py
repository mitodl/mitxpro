"""Management command to fully configure Wagtail"""  # noqa: INP001
from django.core.management.base import BaseCommand

from cms.api import configure_wagtail


class Command(BaseCommand):
    """Ensures that all appropriate changes have been made to Wagtail that will make the site navigable."""  # noqa: E501

    help = __doc__  # noqa: A003

    def handle(self, *args, **options):  # noqa: ARG002
        configure_wagtail()
