"""
Management command to create program certificate(s)

Arguments:
* --user <username/ email> - an email or a username for a user to generate certificate for
* --program <readable_id> - Program readable_id for certificate generation

You must specify --program, since that will be used to filter programs for certificate generation
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from courses.models import CourseRunEnrollment, Program
from courses.utils import generate_program_certificate
from users.api import fetch_user


class Command(BaseCommand):
    """
    Command to create program certificate for users.
    """

    help = "Create program certificate, for a single user or all users in the program."

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
        self,
        *args,  # noqa: ARG002
        **options,
    ):
        """Handle command execution"""
        program = options.get("program")
        if not program:
            raise CommandError("Please provide a valid program readable_id.")  # noqa: EM101

        try:
            program = Program.objects.get(readable_id=program)
        except Program.DoesNotExist:
            raise CommandError(  # noqa: B904
                f"Could not find any program with provided readable_id={program}"  # noqa: EM102
            )

        user = options.get("user") and fetch_user(options["user"])
        base_query = (
            Q(run__course__program=program, user=user)
            if user
            else Q(run__course__program=program)
        )

        enrollments = CourseRunEnrollment.objects.filter(base_query).distinct(
            "user__email", "run__course__program"
        )
        if not enrollments:
            raise CommandError(
                f"Could not find course enrollment(s) with provided program readable_id={program.readable_id}"  # noqa: EM102
            )

        results = []
        for enrollment in enrollments:
            user = enrollment.user
            _, is_created = generate_program_certificate(user, program)

            if _ and not is_created:
                status = (self.style.SUCCESS, "already exists")
            elif not is_created:
                status = (self.style.ERROR, "creation failed")
            else:
                status = (self.style.SUCCESS, "successfully created")

            results.append(
                status[0](f"Certificate {status[1]} for {user} in program {program}")
            )

        for result in results:
            self.stdout.write(result)
