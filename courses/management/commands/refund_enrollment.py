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
        enrollment, enrolled_obj = self.fetch_enrollment(user, options)
        enrollment.deactivate_and_save(ENROLL_CHANGE_STATUS_REFUNDED, no_user=True)
        self.stdout.write(
            self.style.SUCCESS(
                "Refunded enrollment – id: {}, object: {}\nUser: {} ({})".format(
                    enrollment.id,
                    enrolled_obj.title,
                    enrollment.user.username,
                    enrollment.user.email,
                )
            )
        )
