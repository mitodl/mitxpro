"""
Management command to sync grades and certificates for a course run
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from courses.models import ProgramEnrollment
from courses.utils import generate_program_certificate
from users.api import fetch_user


class Command(BaseCommand):
    """
    Command to create program certificates for users.
    """

    help = "Create program certifificates, specific or all, for user(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email or username of the enrolled User",
            required=False,
        )
        parser.add_argument(
            "--readable_id",
            type=str,
            help="The 'readable_id' value for a Program",
            required=True,
        )
        super().add_arguments(parser)

    def handle(
        self, *args, **options
    ):  # pylint: disable=too-many-locals,too-many-branches
        """Handle command execution"""
        program = options["readable_id"]
        user = options["user"] and fetch_user(options["user"])
        base_query = (
            Q(program__readable_id=program, user=user)
            if user
            else Q(program__readable_id=program)
        )

        try:
            enrollments = ProgramEnrollment.objects.filter(base_query)
        except ProgramEnrollment.DoesNotExist:
            raise CommandError(
                "Could not find program enrollment with readable_id={}".format(
                    options["readable_id"]
                )
            )

        results = []
        for enrollment in enrollments:
            user = enrollment.user
            cert, is_created = generate_program_certificate(user, enrollment.program)

            if not cert and not is_created:
                results.append(
                    self.style.ERROR(
                        f"Certificate creation failed for {user.username} ({user.email}) in program {enrollment.program} due to incomplete courses"
                    )
                )
                continue

            results.append(
                self.style.SUCCESS(
                    f"Certificate successfully created for {user.username} ({user.email}) in program {enrollment.program}"
                )
            )

        for result in results:
            self.stdout.write(result)
