"""Management command for loading seed data from JSON file"""
from django.core.management import BaseCommand

from seed import api


class Command(BaseCommand):  # pylint: disable=missing-docstring
    help = "Populate posts and comments from reddit"

    def handle(self, *args, **options):  # pylint: disable=missing-docstring
        self.stdout.write("Loading seed data...")
        seed_results = api.load_and_deserialize_course_data()
        self.stdout.write("Loaded {} programs, {} courses".format(
            len(seed_results.programs),
            len(seed_results.courses)
        ))
