"""
Management command to revoke and un revoke a certificate for a course run or program for the given user.
"""  # noqa: INP001, E501
from django.core.management.base import BaseCommand, CommandError

from courses.utils import revoke_course_run_certificate, revoke_program_certificate
from users.api import fetch_user


class Command(BaseCommand):
    """
    Command to revoke/un-revoke a course run or program certificate for a specified user.
    """  # noqa: E501

    help = (  # noqa: A003
        "Revoke and un revoke a certificate for a specified user against a program or"
        " course run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email or username of the enrolled User",
            required=True,
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--program", type=str, help="The 'readable_id' value for a Program"
        )
        group.add_argument(
            "--run", type=str, help="The 'courseware_id' value for a CourseRun"
        )
        parser.add_argument(
            "--revoke", dest="revoke", action="store_true", required=False
        )
        parser.add_argument(
            "--unrevoke", dest="revoke", action="store_false", required=False
        )
        parser.add_argument(
            "--include-program-courses",
            dest="include_program_courses",
            action="store_true",
            required=False,
            help=(
                "Either should consider the corresponding course runs or not associated"
                " with the program."
            ),
        )

        parser.set_defaults(revoke=True)

        super().add_arguments(parser)

    def handle(
        self, *args, **options  # noqa: ARG002
    ):  # pylint: disable=too-many-locals  # noqa: ARG002, RUF100
        """Handle command execution"""

        user = fetch_user(options["user"]) if options["user"] else None
        program = options.get("program")
        run = options.get("run")
        revoke = options.get("revoke")
        include_program_courses = options.get("include_program_courses")

        if program and run:
            msg = "Either 'program' or 'run' should be provided, not both."
            raise CommandError(msg)
        if not program and not run:
            msg = "Either 'program' or 'run' must be provided."
            raise CommandError(msg)

        if (program or run) and not user:
            msg = "A valid user must be provided."
            raise CommandError(msg)

        updated = False
        if program:
            updated = revoke_program_certificate(
                user=user,
                readable_id=program,
                revoke_state=revoke,
                include_program_courses=include_program_courses,
            )
        elif run:
            updated = revoke_course_run_certificate(
                user=user, courseware_id=run, revoke_state=revoke
            )

        if updated:
            msg = "Certificate for {} has been {}".format(
                f"run: {run}" if run else f"program: {program}",
                "revoked" if revoke else "un-revoked",
            )
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(self.style.WARNING("No changes made."))
