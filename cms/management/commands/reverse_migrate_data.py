"""Management command to setup courseware index pages"""
from django.core.management.base import BaseCommand

from cms.api import reverse_migrate_data


class Command(BaseCommand):
    """Revert the data migration on wagtail models"""

    help = __doc__

    def handle(self, *args, **options):
        reverse_migrate_data()
