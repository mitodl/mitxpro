"""Utility functions/classes for course management commands"""
from requests.exceptions import HTTPError
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import get_user_model

from courses.models import Program, ProgramEnrollment, CourseRun, CourseRunEnrollment
from courseware.api import enroll_in_edx_course_runs

User = get_user_model()


def fetch_user(user_property):
    """
    Attempts to fetch a user based on several properties

    Args:
        user_property (str): The id, email, or username of some User
    Returns:
        User: A user that matches the given property
    """
    if user_property.isdigit():
        return User.objects.get(id=int(user_property))
    else:
        try:
            validate_email(user_property)
            return User.objects.get(email=user_property)
        except ValidationError:
            return User.objects.get(username=user_property)


class EnrollmentChangeCommand(BaseCommand):
    """Base class for management commands that change enrollment status"""

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            dest="force",
            help="Ignores validation when performing the desired status change",
        )

    def handle(self, *args, **options):
        pass

    @staticmethod
    def fetch_enrollment(user, command_options):
        """
        Fetches the appropriate enrollment model object paired with an object of the
        Program/Course that the user is enrolled in.

        Args:
            user (User): An enrolled User
            command_options (dict): A dict of command parameters
        Returns:
             tuple: (ProgramEnrollment, Program) or (CourseRunEnrollment, CourseRun)
        """
        program_property = command_options["program"]
        run_property = command_options["run"]
        force = command_options["force"]

        if program_property and run_property:
            raise CommandError(
                "Either 'program' or 'run' should be provided, not both."
            )
        elif not program_property and not run_property:
            raise CommandError("Either 'program' or 'run' must be provided.")

        if program_property:
            enrolled_obj = Program.objects.get(readable_id=program_property)
            enrollment = ProgramEnrollment.all_objects.filter(
                user=user, program=enrolled_obj
            ).first()
        else:
            enrolled_obj = CourseRun.objects.get(courseware_id=run_property)
            enrollment = CourseRunEnrollment.all_objects.filter(
                user=user, run=enrolled_obj
            ).first()

        if not enrollment:
            raise CommandError("Enrollment not found for: {}".format(enrolled_obj))
        elif not enrollment.active and not force:
            raise CommandError(
                "The given enrollment is not active ({}).\n"
                "Add the -f/--force flag if you want to change the status anyway.".format(
                    enrollment.id
                )
            )

        return enrollment, enrolled_obj

    def move_course_run_enrollment(
        self, existing_enrollment, change_status, to_run=None, to_user=None
    ):
        """
        Helper method for moving a CourseRunEnrollment from one user/run to another. This
        takes care of creating the new CourseRunEnrollment, deactivating the existing one,
        and attempting to enroll the 'to' user in the given course run in edX.

        Args:
            existing_enrollment (CourseRunEnrollment): The enrollment to 'move'
            change_status (str): The status that will be set on the existing enrollment
            to_run (CourseRun or None): The course run to use for the new enrollment.
                If blank, the new enrollment gets the existing enrollment's course run.
            to_user (User or None): The user to use for the new enrollment.
                If blank, the new enrollment gets the existing enrollment's user.

        Returns:
            CourseRunEnrollment: The enrollment record that was created
        """
        to_user = to_user or existing_enrollment.user
        to_run = to_run or existing_enrollment.run
        to_enrollment = CourseRunEnrollment.objects.create(
            user=to_user, run=to_run, company=existing_enrollment.company
        )
        existing_enrollment.deactivate_and_save(change_status, no_user=True)
        self.stdout.write(
            "Current course run enrollment deactivated and new enrollment record created. "
            "Attempting to enroll the user {} ({}) in {} on edX...".format(
                to_user.username, to_user.email, to_run.courseware_id
            )
        )
        self.enroll_in_edx(to_user, [to_run])
        return to_enrollment

    def enroll_in_edx(self, user, course_runs):
        """
        Try to perform edX enrollment, but print a message and continue if it fails

        Args:
            user (User): The user to enroll
            course_runs (iterable of CourseRun): The course runs to enroll in
        """
        try:
            enroll_in_edx_course_runs(user, course_runs)
        except HTTPError as exc:
            self.stdout.write(
                self.style.WARNING(
                    "edX enrollment request failed ({}).\nResponse: {}".format(
                        exc.response.status_code, exc.response.text
                    )
                )
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.stdout.write(
                self.style.WARNING(
                    "Unexpected edX enrollment error.\n{}".format(str(exc))
                )
            )
