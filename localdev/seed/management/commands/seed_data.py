"""Management command to create or update seed data"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from localdev.seed.api import SeedDataLoader, get_raw_seed_data_from_file

User = get_user_model()


class Command(BaseCommand):
    """Creates or updates seed data based on a raw seed data file"""

    help = "Creates or updates seed data based on a raw seed data file"

    def handle(self, *args, **options):
        """Handle command execution"""
        seed_data_loader = SeedDataLoader()
        raw_seed_data = get_raw_seed_data_from_file()
        results = seed_data_loader.create_seed_data(raw_seed_data)

        if not any(results.report.values()):
            self.stdout.write(self.style.WARNING("No changes made."))
        else:
            self.stdout.write(self.style.SUCCESS("RESULTS"))
            for k, v in results.report.items():
                self.stdout.write("{}: {}".format(k, v))
