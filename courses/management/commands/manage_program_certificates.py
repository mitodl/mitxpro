"""
Management command to create program certificate(s)

Arguments:
* --user <username/ email> - an email or a username for a user to generate certificate for
* --program <readable_id> - Program readable_id for certificate generation

You must specify --program, since that will be used to filter programs for certificate generation
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from courses.models import CourseRunEnrollment
from courses.utils import generate_program_certificate
from users.api import fetch_user


class Command(BaseCommand):
    """
    Command to create program certificate for users.
    """

    help = "Create program certifificate, specific or all, for user(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email or username of the enrolled User",
            required=False,
        )
        parser.add_argument(
            "--program",
            type=str,
            help="The 'readable_id' value for a Program",
            required=True,
        )
        super().add_arguments(parser)

    def handle(
        self, *args, **options
    ):  # pylint: disable=too-many-locals,too-many-branches
        """Handle command execution"""
        program = options.get("program")
        if not program:
            raise CommandError("Please provide a valid program readable_id.")

        user = options.get("user") and fetch_user(options["user"])
        base_query = (
            Q(run__course__program__readable_id=program, active=True, user=user)
            if user
            else Q(run__course__program__readable_id=program, active=True)
        )

        enrollments = CourseRunEnrollment.objects.filter(base_query).distinct('user__email', 'run__course__program')
        if not enrollments:
            raise CommandError(
                f"Could not find course enrollment(s) with provided program readable_id={program}"
            ) 

        results = []
        for enrollment in enrollments:
            user = enrollment.user
            course_program = enrollment.run.course.program
            _, is_created = generate_program_certificate(user, course_program)

            if not is_created:
                status = "failed"
            else:
                status = "successful"

            results.append(
                self.style.SUCCESS(
                    f"Certificate creation {status} for {user} in program {course_program}"
                )
            )

        for result in results:
            self.stdout.write(result)
