"""
Management command to create program certificate(s)

Arguments:
* --user <username/ email> - an email or a username for a user to generate certificate for
* --program <readable_id> - Program readable_id for certificate generation

You must specify --program, since that will be used to filter programs for certificate generation
"""  # noqa: INP001, E501
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from courses.models import CourseRunEnrollment, Program
from courses.utils import generate_program_certificate
from users.api import fetch_user


class Command(BaseCommand):
    """
    Command to create program certificate for users.
    """

    help = "Create program certificate, for a single user or all users in the program."  # noqa: A003, E501

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
        self, *args, **options  # noqa: ARG002
    ):  # pylint: disable=too-many-locals,too-many-branches
        """Handle command execution"""
        program = options.get("program")
        if not program:
            msg = "Please provide a valid program readable_id."
            raise CommandError(msg)

        try:
            program = Program.objects.get(readable_id=program)
        except Program.DoesNotExist:
            msg = f"Could not find any program with provided readable_id={program}"
            raise CommandError(msg)  # noqa: B904, TRY200

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
            msg = f"Could not find course enrollment(s) with provided program readable_id={program.readable_id}"  # noqa: E501
            raise CommandError(msg)

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
