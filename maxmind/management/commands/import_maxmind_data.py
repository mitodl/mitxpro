"""
Imports the MaxMind GeoLite2 databases. (Or, acts as a thin wrapper around the
API call that does.)
"""  # noqa: INP001

from os import path

from django.core.management import BaseCommand, CommandError

from maxmind import api


class Command(BaseCommand):
    """
    Imports the MaxMind GeoLite2 databases.
    """

    help = "Imports the MaxMind GeoLite2 databases."  # noqa: A003

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

    def handle(self, *args, **kwargs):  # noqa: ARG002
        if not path.exists(kwargs["file"]):  # noqa: PTH110
            msg = f"Input file {kwargs['file']} does not exist."
            raise CommandError(msg)

        api.import_maxmind_database(kwargs["filetype"], kwargs["file"])

        self.stdout.write(self.style.SUCCESS("Import completed!"))
