"""Management command to sync external course runs"""

from django.core.management.base import BaseCommand

from courses.models import Platform
from courses.sync_external_courses.external_course_sync_api import (
    EXTERNAL_COURSE_VENDOR_KEYMAPS,
    fetch_external_courses,
    update_external_course_runs,
)
from ecommerce.mail_api import send_external_data_sync_email


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
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            dest="force",
            help="Sync courses even if the daily sync is off.",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""
        vendor_name = options["vendor_name"]
        keymap = EXTERNAL_COURSE_VENDOR_KEYMAPS.get(vendor_name.lower())
        platform = Platform.objects.filter(name__iexact=vendor_name).first()

        if not platform:
            self.stdout.write(self.style.ERROR(f"Unknown vendor name {vendor_name}."))
            return

        if not keymap:
            self.stdout.write(
                self.style.ERROR(f"Mapping does not exist for {vendor_name}.")
            )
            return

        if not platform.enable_sync and not options.get("force"):
            self.stdout.write(
                self.style.ERROR(
                    f"Course sync is off for {vendor_name}. Please enable it before syncing."
                )
            )
            return

        self.stdout.write(f"Starting course sync for {vendor_name}.")
        keymap = keymap()
        external_course_runs = fetch_external_courses(keymap)
        stats_collector = update_external_course_runs(external_course_runs, keymap)

        email_stats = stats_collector.email_stats()

        send_external_data_sync_email(
            vendor_name=vendor_name,
            stats=email_stats,
        )
        stats_collector.log_stats(self)
        self.stdout.write(
            self.style.SUCCESS(f"External course sync successful for {vendor_name}.")
        )

    def log_style_success(self, log_msg):
        """
        Logs success styled message.

        Args:
            log_msg(str): Log message.
        """
        self.stdout.write(self.style.SUCCESS(log_msg))
