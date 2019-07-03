"""Management command to change enrollment status"""
from django.contrib.auth import get_user_model

from courses.management.utils import EnrollmentChangeCommand, fetch_user
from courses.constants import ENROLL_CHANGE_STATUS_REFUNDED

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'refunded' and deactivates it"""

    help = "Sets a user's enrollment to 'refunded' and deactivates it"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="The id, email, or username of the enrolled User"
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--program",
            type=str,
            help="The 'readable_id' value for an enrolled Program",
        )
        group.add_argument(
            "--run",
            type=str,
            help="The 'courseware_id' value for an enrolled CourseRun",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):
        """Handle command execution"""
        user = fetch_user(options["user"])
        enrollment, _ = self.fetch_enrollment(user, options)
        if options["program"]:
            program_enrollment, run_enrollments = self.deactivate_program_enrollment(
                enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
            )
        else:
            program_enrollment = None
            run_enrollments = [
                self.deactivate_run_enrollment(
                    enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
                )
            ]

        self.stdout.write(
            self.style.SUCCESS(
                "Refunded enrollments for user: {} ({})\nEnrollments affected: {}".format(
                    enrollment.user.username,
                    enrollment.user.email,
                    list(filter(bool, [program_enrollment] + run_enrollments)),
                )
            )
        )
