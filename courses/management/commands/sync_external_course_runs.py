"""Management command to sync external course runs"""

from django.core.management.base import BaseCommand

from courses.constants import EMERITUS_PLATFORM_NAME
from courses.tasks import task_sync_emeritus_course_runs


class Command(BaseCommand):
    """Sync external course runs"""

    help = "Management command to sync external course runs from the vendor APIs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--vendor_name",
            type=str,
            help="The name of the vendor i.e. `Emeritus`",
            required=True,
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""
        vendor_name = options["vendor_name"]
        sync_course_runs_task_to_vendor_map = {
            EMERITUS_PLATFORM_NAME.lower(): task_sync_emeritus_course_runs
        }
        course_runs_sync_task = sync_course_runs_task_to_vendor_map.get(
            vendor_name.lower(), None
        )
        if course_runs_sync_task:
            course_runs_sync_task.delay()
            self.stdout.write(
                self.style.SUCCESS(
                    f"External Course Sync task is triggered successfully for {vendor_name}."
                )
            )
