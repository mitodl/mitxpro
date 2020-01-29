"""Management command to change enrollment status"""
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

from courses.api import deactivate_run_enrollment
from courses.management.utils import EnrollmentChangeCommand, enrollment_summary
from courses.constants import ENROLL_CHANGE_STATUS_DEFERRED
from courses.models import CourseRun, CourseRunEnrollment
from users.api import fetch_user

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'deferred' and creates an enrollment for a different course run"""

    help = "Sets a user's enrollment to 'deferred' and creates an enrollment for a different course run"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email, or username of the enrolled User",
            required=True,
        )
        parser.add_argument(
            "--from-run",
            type=str,
            help="The 'courseware_id' value for an enrolled CourseRun",
            required=True,
        )
        parser.add_argument(
            "--to-run",
            type=str,
            help="The 'courseware_id' value for the CourseRun that you are deferring to",
            required=True,
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):
        """Handle command execution"""
        user = fetch_user(options["user"])
        from_run = CourseRun.objects.filter(courseware_id=options["from_run"]).first()
        to_run = CourseRun.objects.filter(courseware_id=options["to_run"]).first()
        if not from_run:
            raise CommandError(
                "Could not find 'from' run with courseware_id={}".format(
                    options["from_run"]
                )
            )
        elif not to_run:
            raise CommandError(
                "Could not find 'to' run with courseware_id={}".format(
                    options["to_run"]
                )
            )
        elif from_run.course != to_run.course and not options["force"]:
            raise CommandError(
                "Enrollment deferral must occur between two runs of the same course "
                "('from' run course: {}, 'to' run course: {})\n"
                "Add the -f/--force flag if you want to complete this deferment anyway.".format(
                    from_run.course.title, to_run.course.title
                )
            )
        elif not to_run.is_unexpired and not options["force"]:
            raise CommandError("'to' run is expired")

        from_enrollment = CourseRunEnrollment.all_objects.get(user=user, run=from_run)
        if not from_enrollment.active and not options["force"]:
            raise CommandError(
                "The 'from' enrollment is not active ({}).\n"
                "Add the -f/--force flag if you want to complete this deferment anyway.".format(
                    from_enrollment.id
                )
            )

        to_enrollment = self.create_run_enrollment(from_enrollment, to_run=to_run)
        deactivate_run_enrollment(
            from_enrollment, change_status=ENROLL_CHANGE_STATUS_DEFERRED
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Deferred enrollment for user: {} ({})\nEnrollment created/updated: {}".format(
                    user.username, user.email, enrollment_summary(to_enrollment)
                )
            )
        )
