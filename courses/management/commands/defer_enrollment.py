"""Management command to change enrollment status"""
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

from courses.management.utils import EnrollmentChangeCommand, fetch_user
from courses.constants import ENROLL_CHANGE_STATUS_DEFERRED
from courses.models import CourseRun, CourseRunEnrollment

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'deferred' and creates an enrollment for a different course run"""

    help = "Sets a user's enrollment to 'deferred' and creates an enrollment for a different course run"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="The id, email, or username of the enrolled User"
        )
        parser.add_argument(
            "--from-run",
            type=str,
            help="The 'courseware_id' value for an enrolled CourseRun",
        )
        parser.add_argument(
            "--to-run",
            type=str,
            help="The 'courseware_id' value for the CourseRun that you are deferring to",
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
        elif not to_run.is_unexpired:
            raise CommandError("'To' run is expired")

        from_enrollment = CourseRunEnrollment.all_objects.get(user=user, run=from_run)
        if not from_enrollment.active and not options["force"]:
            raise CommandError(
                "The 'from' enrollment is not active ({}).\n"
                "Add the -f/--force flag if you want to complete this deferment anyway.".format(
                    from_enrollment.id
                )
            )

        to_enrollment = self.move_course_run_enrollment(
            from_enrollment, change_status=ENROLL_CHANGE_STATUS_DEFERRED, to_run=to_run
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Deferred enrollment – 'from' run id: {}, 'to' run id: {}\nUser: {} ({})".format(
                    from_enrollment.run.id,
                    to_enrollment.run.id,
                    user.username,
                    user.email,
                )
            )
        )
