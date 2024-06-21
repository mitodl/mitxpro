"""Management command to sync external course runs"""

from django.core.management.base import BaseCommand

from courses.sync_external_courses.emeritus_api import EMERITUS_PLATFORM_NAME
from courses.tasks import task_sync_emeritus_course_runs
from mitxpro import settings


class Command(BaseCommand):
    """Sync external course runs"""

    help = "Management command to sync external course runs from the vendor APIs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--vendor-name",
            type=str,
            help="The name of the vendor i.e. `Emeritus`",
            required=True,
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""
        if not settings.FEATURES.get("ENABLE_EXTERNAL_COURSE_SYNC", False):
            self.stdout.write(
                self.style.ERROR(
                    "External Course Sync is disabled. You can enable by turning the feature flag "
                    "`ENABLE_EXTERNAL_COURSE_SYNC`"
                )
            )
            return
        vendor_name = options["vendor_name"]
        sync_course_to_vendor_task_map = {
            EMERITUS_PLATFORM_NAME.lower(): task_sync_emeritus_course_runs
        }
        courses_sync_task = sync_course_to_vendor_task_map.get(
            vendor_name.lower(), None
        )
        if courses_sync_task:
            self.stdout.write(f"Starting Course Sync for {vendor_name}.")
            courses_sync_task()
            self.stdout.write(
                self.style.SUCCESS(
                    f"External Course Sync successful for {vendor_name}."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"There is no task to sync courses for {vendor_name}.")
            )
