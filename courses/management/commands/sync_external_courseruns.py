"""Management command to sync external courseware"""

from django.core.management.base import BaseCommand

from courses.tasks import task_sync_emeritus_courseruns


class Command(BaseCommand):
    """Sync external courseware"""

    help = "Management command to sync external courseware from the vendor APIs."

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
        sync_courseruns_task_to_vendor_map = {
            "emeritus": task_sync_emeritus_courseruns
        }
        courseruns_sync_task = sync_courseruns_task_to_vendor_map.get(vendor_name.lower(), None)
        if courseruns_sync_task:
            courseruns_sync_task()
