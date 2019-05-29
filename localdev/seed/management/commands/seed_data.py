"""Management command to create or delete seed data"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from localdev.seed.api import SeedDataLoader, get_raw_seed_data_from_file

User = get_user_model()


class Command(BaseCommand):
    """Creates or deletes seed data based on a raw seed data file"""

    help = "Creates or deletes seed data based on a raw seed data file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            dest="delete",
            help="Delete existing seed data instead of creating it.",
        )

    def handle(self, *args, **options):
        """Handle command execution"""
        delete = options["delete"]
        seed_data_loader = SeedDataLoader()
        raw_seed_data = get_raw_seed_data_from_file()
        results = (
            seed_data_loader.create_seed_data(raw_seed_data)
            if not delete
            else seed_data_loader.delete_seed_data(raw_seed_data)
        )

        if not any(results.report.values()):
            self.stdout.write(self.style.WARNING("No changes made."))
        else:
            self.stdout.write(self.style.SUCCESS("RESULTS"))
            for k, v in results.report.items():
                self.stdout.write("{}: {}".format(k, v))
