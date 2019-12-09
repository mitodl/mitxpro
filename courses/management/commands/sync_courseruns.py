"""
Management command to sync dates and title for all or a specific course run from edX
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from courses.models import CourseRun
from courses.utils import sync_course_runs
from mitxpro.utils import now_in_utc


class Command(BaseCommand):
    """
    Command to sync course run dates and title from edX.
    """

    help = "Sync dates and title for all or a specific course run from edX."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            type=str,
            help="The 'courseware_id' value for a CourseRun",
            required=False,
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        """Handle command execution"""
        runs = []
        if options["run"]:
            try:
                runs = [CourseRun.objects.get(courseware_id=options["run"])]
            except CourseRun.DoesNotExist:
                raise CommandError(
                    "Could not find run with courseware_id={}".format(options["run"])
                )
        else:
            # We pick up all the course runs that do not have an expiration date (implies not having
            # an end_date) or those that are not expired yet, in case the user has not specified any
            # course run id.
            now = now_in_utc()
            runs = CourseRun.objects.live().filter(
                Q(expiration_date__isnull=True) | Q(expiration_date__gt=now)
            )

        success_count, error_count = sync_course_runs(runs)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: {success_count} updated, {error_count} failures"
            )
        )
