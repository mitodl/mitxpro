"""Management command to change enrollment status"""
from django.contrib.auth import get_user_model

from courses.management.utils import EnrollmentChangeCommand, enrollment_summaries
from courses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from ecommerce.models import Order
from users.api import fetch_user

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'refunded' and deactivates it"""

    help = "Sets a user's enrollment to 'refunded' and deactivates it"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email, or username of the enrolled User",
            required=True,
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
        parser.add_argument(
            "--order", type=str, help="The 'order_id' value for an user's order ID."
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

        success_msg = "Refunded enrollments for user: {} ({})\nEnrollments affected: {}".format(
            enrollment.user.username,
            enrollment.user.email,
            enrollment_summaries(filter(bool, [program_enrollment] + run_enrollments)),
        )

        if enrollment.order:
            enrollment.order.status = Order.REFUNDED
            enrollment.order.save_and_log(None)
            success_msg += "\nOrder status set to '{}' (order id: {})".format(
                enrollment.order.status, enrollment.order.id
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "The given enrollment is not associated with an order, so no order status will be changed."
                )
            )

        self.stdout.write(self.style.SUCCESS(success_msg))
