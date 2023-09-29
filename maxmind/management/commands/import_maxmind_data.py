"""
Imports the MaxMind GeoLite2 databases. (Or, acts as a thin wrapper around the
API call that does.)
"""

from django.core.management import BaseCommand, CommandError
from os import path

from maxmind import api


class Command(BaseCommand):
    """
    Imports the MaxMind GeoLite2 databases.
    """

    help = "Imports the MaxMind GeoLite2 databases."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "file",
            type=str,
            help="The CSV-format file to import.",
        )

        parser.add_argument(
            "filetype",
            choices=api.MAXMIND_CSV_TYPES,
            type=str,
            help="The type of file being imported.",
        )

    def handle(self, *args, **kwargs):
        if not path.exists(kwargs["file"]):
            raise CommandError(f"Input file {kwargs['file']} does not exist.")

        api.import_maxmind_database(kwargs["filetype"], kwargs["file"])

        self.stdout.write(self.style.SUCCESS("Import completed!"))
