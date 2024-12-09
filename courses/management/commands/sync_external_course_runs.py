"""Management command to sync external course runs"""

from django.core.management.base import BaseCommand

from courses.sync_external_courses.external_course_sync_api import (
    EXTERNAL_COURSE_VENDOR_KEYMAPS,
    fetch_external_courses,
    update_external_course_runs,
)
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
                    "External Course Sync is disabled. You can enable it by turning on the feature flag "
                    "`ENABLE_EXTERNAL_COURSE_SYNC`"
                )
            )
            return

        vendor_name = options["vendor_name"]
        keymap = EXTERNAL_COURSE_VENDOR_KEYMAPS.get(vendor_name.lower())
        if not keymap:
            self.stdout.write(self.style.ERROR(f"Unknown vendor name {vendor_name}."))
            return

        self.stdout.write(f"Starting course sync for {vendor_name}.")
        keymap = keymap()
        external_course_runs = fetch_external_courses(keymap)
        stats = update_external_course_runs(external_course_runs, keymap)
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
        self.log_style_success(
            f"Number of Courses Created {len(stats['courses_created'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('courses_created') or 0}.\n"
        )
        self.log_style_success(
            f"Number of existing Courses {len(stats['existing_courses'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('existing_courses') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Course Runs Created {len(stats['course_runs_created'])}."
        )
        self.log_style_success(
            f"External Course Run Codes: {stats.get('course_runs_created') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Course Runs Updated {len(stats['course_runs_updated'])}."
        )
        self.log_style_success(
            f"External Course Run Codes: {stats.get('course_runs_updated') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Products Created {len(stats['products_created'])}."
        )
        self.log_style_success(
            f"Course Run courseware_ids: {stats.get('products_created') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Product Versions Created {len(stats['product_versions_created'])}."
        )
        self.log_style_success(
            f"Course Run courseware_ids: {stats.get('product_versions_created') or 0}.\n"
        )
        self.log_style_success(
            f"Course Runs without prices: {stats.get('course_runs_without_prices') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Course Pages Created {len(stats['course_pages_created'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('course_pages_created') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Course Pages Updated {len(stats['course_pages_updated'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('course_pages_updated') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Certificate Pages Created {len(stats['certificates_created'])}."
        )
        self.log_style_success(
            f"Course Readable IDs: {stats.get('certificates_created') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Certificate Pages Updated {len(stats['certificates_updated'])}."
        )
        self.log_style_success(
            f"Course Readable IDs: {stats.get('certificates_updated') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Course Runs Skipped due to bad data {len(stats['course_runs_skipped'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('course_runs_skipped') or 0}.\n"
        )
        self.log_style_success(
            f"Number of Expired Course Runs {len(stats['course_runs_expired'])}."
        )
        self.log_style_success(
            f"External Course Codes: {stats.get('course_runs_expired') or 0}.\n"
        )

    def log_style_success(self, log_msg):
        """
        Logs success styled message.

        Args:
            log_msg(str): Log message.
        """
        self.stdout.write(self.style.SUCCESS(log_msg))
