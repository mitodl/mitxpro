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
            # Create the program enrollment
            ProgramEnrollment.objects.create(
                user=to_user,
                program=enrolled_obj,
                company=enrollment.company,
                order=enrollment.order,
            )
            associated_run_enrollments = CourseRunEnrollment.objects.filter(
                user=from_user, run__course__program=enrolled_obj
            )
            # Create enrollments in all of the same program course runs that the 'from' user
            # was enrolled in
            for run_enrollment in associated_run_enrollments:
                CourseRunEnrollment.objects.create(
                    user=to_user,
                    run=run_enrollment.run,
                    company=enrollment.company,
                    order=enrollment.order,
                )
            enrollments_to_deactivate = [enrollment] + list(associated_run_enrollments)
            runs_to_enroll = [e.run for e in associated_run_enrollments]
        else:
            CourseRunEnrollment.objects.create(
                user=to_user,
                run=enrolled_obj,
                company=enrollment.company,
                order=enrollment.order,
            )
            enrollments_to_deactivate = [enrollment]
            runs_to_enroll = [enrolled_obj]

        for enrollment_to_deactivate in enrollments_to_deactivate:
            enrollment_to_deactivate.active = False
            enrollment_to_deactivate.change_status = ENROLL_CHANGE_STATUS_TRANSFERRED
            enrollment_to_deactivate.save_and_log(None)

        self.stdout.write(
            "New enrollment record(s) created. Attempting to enroll the user on edX..."
        )
        self.enroll_in_edx(to_user, runs_to_enroll)

        self.stdout.write(
            self.style.SUCCESS(
                "Transferred enrollment – 'from' user: {} ({}), 'to' user: {} ({})\n"
                "Enrollment in: {}".format(
                    from_user.username,
                    from_user.email,
                    to_user.username,
                    to_user.email,
                    enrolled_obj,
                )
            )
        )
