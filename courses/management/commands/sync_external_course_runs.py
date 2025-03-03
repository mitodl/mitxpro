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
        stats = update_external_course_runs(external_course_runs, keymap)
        send_external_data_sync_email(
            vendor_name=vendor_name,
            stats=stats,
        )
        self.log_stats(stats)
        self.stdout.write(
            self.style.SUCCESS(f"External course sync successful for {vendor_name}.")
        )

    def log_stats(self, stats):
        """
        Logs the stats for the external course sync.

        Args:
            stats(dict): Dict containing results for the objects created/updated.
        """

        def extract_first_item(data_set):
            return {item[0] for item in data_set} if data_set else set()

        def log_stat(category, key, label):
            items = extract_first_item(stats.get(key, set()))
            self.log_style_success(f"Number of {category}: {len(items)}.")
            self.log_style_success(f"{label}: {items or 0}\n")

        log_stat("Courses Created", "courses_created", "External Course Codes")
        log_stat("Existing Courses", "existing_courses", "External Course Codes")
        log_stat(
            "Course Runs Created", "course_runs_created", "External Course Run Codes"
        )
        log_stat(
            "Course Runs Updated", "course_runs_updated", "External Course Run Codes"
        )
        log_stat("Products Created", "products_created", "Course Run courseware_ids")
        log_stat(
            "Product Versions Created",
            "product_versions_created",
            "Course Run courseware_ids",
        )
        log_stat(
            "Course Runs without prices",
            "course_runs_without_prices",
            "External Course Codes",
        )
        log_stat(
            "Course Pages Created", "course_pages_created", "External Course Codes"
        )
        log_stat(
            "Course Pages Updated", "course_pages_updated", "External Course Codes"
        )
        log_stat(
            "Certificate Pages Created", "certificates_created", "Course Readable IDs"
        )
        log_stat(
            "Certificate Pages Updated", "certificates_updated", "Course Readable IDs"
        )
        log_stat(
            "Course Runs Skipped due to bad data",
            "course_runs_skipped",
            "External Course Run Codes",
        )
        log_stat(
            "Expired Course Runs", "course_runs_expired", "External Course Run Codes"
        )
        log_stat(
            "Course Runs Deactivated",
            "course_runs_deactivated",
            "External Course Run Codes",
        )

    def log_style_success(self, log_msg):
        """
        Logs success styled message.

        Args:
            log_msg(str): Log message.
        """
        self.stdout.write(self.style.SUCCESS(log_msg))
