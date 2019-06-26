"""Management command to change enrollment status"""
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

from courses.management.utils import EnrollmentChangeCommand, fetch_user
from courses.constants import ENROLL_CHANGE_STATUS_TRANSFERRED
from courses.models import CourseRunEnrollment, ProgramEnrollment

User = get_user_model()


class Command(EnrollmentChangeCommand):
    """Sets a user's enrollment to 'transferred' and creates an enrollment for a different user"""

    help = "Sets a user's enrollment to 'transferred' and creates an enrollment for a different user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-user",
            type=str,
            help="The id, email, or username of the enrolled User",
        )
        parser.add_argument(
            "--to-user",
            type=str,
            help="The id, email, or username of the User to whom the enrollment will be transferred",
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
        from_user = fetch_user(options["from_user"])
        to_user = fetch_user(options["to_user"])
        enrollment, enrolled_obj = self.fetch_enrollment(from_user, options)

        new_enrollments = []
        if options["program"]:
            to_user_existing_enrolled_run_ids = CourseRunEnrollment.all_objects.filter(
                user=to_user, run__course__program=enrolled_obj
            ).values_list("run__courseware_id", flat=True)
            if len(to_user_existing_enrolled_run_ids) > 0:
                raise CommandError(
                    "'to' user is already enrolled in program runs ({})".format(
                        str(to_user_existing_enrolled_run_ids)
                    )
                )

            # Create the program enrollment, and deactivate the existing one
            new_enrollments.append(
                ProgramEnrollment.objects.create(
                    user=to_user, program=enrolled_obj, company=enrollment.company
                )
            )
            enrollment.deactivate_and_save(
                ENROLL_CHANGE_STATUS_TRANSFERRED, no_user=True
            )

            run_enrollments_to_move = CourseRunEnrollment.objects.filter(
                user=from_user, run__course__program=enrolled_obj
            )
        else:
            run_enrollments_to_move = [enrollment]

        new_course_run_enrollments = [
            self.move_course_run_enrollment(
                run_enrollment, ENROLL_CHANGE_STATUS_TRANSFERRED, to_user=to_user
            )
            for run_enrollment in run_enrollments_to_move
        ]
        new_enrollments.extend(new_course_run_enrollments)

        self.stdout.write(
            self.style.SUCCESS(
                "Transferred enrollment – 'from' user: {} ({}), 'to' user: {} ({})\n"
                "Enrollments created: {}".format(
                    from_user.username,
                    from_user.email,
                    to_user.username,
                    to_user.email,
                    new_enrollments,
                )
            )
        )
