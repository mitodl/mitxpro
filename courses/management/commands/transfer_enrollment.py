"""Management command to change enrollment status"""
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

from courses.api import deactivate_program_enrollment, deactivate_run_enrollment
from courses.management.utils import EnrollmentChangeCommand, enrollment_summaries
from courses.constants import ENROLL_CHANGE_STATUS_TRANSFERRED
from courses.models import CourseRunEnrollment
from users.api import fetch_user

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'transferred' and creates an enrollment for a different user"""

    help = "Sets a user's enrollment to 'transferred' and creates an enrollment for a different user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-user",
            type=str,
            help="The id, email, or username of the enrolled User",
            required=True,
        )
        parser.add_argument(
            "--to-user",
            type=str,
            help="The id, email, or username of the User to whom the enrollment will be transferred",
            required=True,
        )
        parser.add_argument(
            "--order", type=str, help="The 'order_id' value for an user's order ID."
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
            "-k",
            "--keep-failed-enrollments",
            action="store_true",
            dest="keep_failed_enrollments",
            help="If provided, enrollment records will be kept even if edX enrollment fails",
        )

        super().add_arguments(parser)

    def handle(self, *args, **options):
        from_user = fetch_user(options["from_user"])
        to_user = fetch_user(options["to_user"])
        keep_failed_enrollments = options["keep_failed_enrollments"]
        enrollment, enrolled_obj = self.fetch_enrollment(from_user, options)

        if options["program"]:
            to_user_existing_enrolled_run_ids = CourseRunEnrollment.get_program_run_enrollments(
                user=to_user, program=enrolled_obj
            ).values_list(
                "run__courseware_id", flat=True
            )
            if len(to_user_existing_enrolled_run_ids) > 0:
                raise CommandError(
                    "'to' user is already enrolled in program runs ({})".format(
                        list(to_user_existing_enrolled_run_ids)
                    )
                )

            new_program_enrollment, new_run_enrollments = self.create_program_enrollment(
                enrollment,
                to_user=to_user,
                keep_failed_enrollments=keep_failed_enrollments,
            )
            if new_program_enrollment and new_run_enrollments:
                deactivate_program_enrollment(
                    enrollment,
                    change_status=ENROLL_CHANGE_STATUS_TRANSFERRED,
                    keep_failed_enrollments=keep_failed_enrollments,
                )
        else:
            new_program_enrollment = None
            new_run_enrollment = self.create_run_enrollment(
                enrollment,
                to_user=to_user,
                keep_failed_enrollments=keep_failed_enrollments,
            )
            new_run_enrollments = []
            if new_run_enrollment:
                new_run_enrollments.append(new_run_enrollment)
                deactivate_run_enrollment(
                    enrollment,
                    change_status=ENROLL_CHANGE_STATUS_TRANSFERRED,
                    keep_failed_enrollments=keep_failed_enrollments,
                )

        if new_program_enrollment or new_run_enrollments:
            self.stdout.write(
                self.style.SUCCESS(
                    "Transferred enrollment – 'from' user: {} ({}), 'to' user: {} ({})\n"
                    "Enrollments created/updated: {}".format(
                        from_user.username,
                        from_user.email,
                        to_user.username,
                        to_user.email,
                        enrollment_summaries(
                            filter(bool, [new_program_enrollment] + new_run_enrollments)
                        ),
                    )
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Failed to transfer enrollment – 'from' user: {} ({}), 'to' user: {} ({})\n".format(
                        from_user.username,
                        from_user.email,
                        to_user.username,
                        to_user.email,
                    )
                )
            )
