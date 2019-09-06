"""Utility functions/classes for course management commands"""
from functools import partial

from django.core.management.base import BaseCommand, CommandError

from courses.models import CourseRun, CourseRunEnrollment, Program, ProgramEnrollment
from courseware.api import enroll_in_edx_course_runs
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
)
from ecommerce import mail_api
from mitxpro.utils import has_equal_properties


def enrollment_summary(enrollment):
    """
    Returns a string representation of an enrollment for command output

    Args:
        enrollment (ProgramEnrollment or CourseRunEnrollment): The enrollment
    Returns:
        str: A string representation of an enrollment
    """
    if isinstance(enrollment, ProgramEnrollment):
        return "<ProgramEnrollment for {}>".format(enrollment.program.text_id)
    else:
        return "<CourseRunEnrollment for {}>".format(enrollment.run.text_id)


def enrollment_summaries(enrollments):
    """
    Returns a list of string representations of enrollments for command output

    Args:
        enrollments (iterable of ProgramEnrollment or CourseRunEnrollment): The enrollments
    Returns:
        list of str: A list of string representations of enrollments
    """
    return list(map(enrollment_summary, enrollments))


def create_or_update_enrollment(model_cls, defaults=None, **kwargs):
    """Creates or updates an enrollment record"""
    defaults = {**(defaults or {}), "active": True, "change_status": None}
    enrollment, created = model_cls.all_objects.get_or_create(
        **kwargs, defaults=dict(**defaults)
    )
    if not created and not has_equal_properties(enrollment, defaults):
        for field_name, field_value in defaults.items():
            setattr(enrollment, field_name, field_value)
        enrollment.save_and_log(None)
    return enrollment, created


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

    def deactivate_program_enrollment(self, program_enrollment, change_status):
        """
        Helper method to deactivate a ProgramEnrollment

        Args:
            program_enrollment (ProgramEnrollment): The program enrollment to deactivate
            change_status (str): The change status to set on the enrollment when deactivating
        Returns:
            tuple of ProgramEnrollment, list(CourseRunEnrollment): The deactivated enrollments
        """
        program_enrollment.deactivate_and_save(change_status, no_user=True)
        program_run_enrollments = program_enrollment.get_run_enrollments()
        return (
            program_enrollment,
            list(
                map(
                    partial(
                        self.deactivate_run_enrollment, change_status=change_status
                    ),
                    program_run_enrollments,
                )
            ),
        )

    @staticmethod
    def deactivate_run_enrollment(run_enrollment, change_status):
        """
        Helper method to deactivate a CourseRunEnrollment

        Args:
            run_enrollment (CourseRunEnrollment): The course run enrollment to deactivate
            change_status (str): The change status to set on the enrollment when deactivating
        Returns:
            CourseRunEnrollment: The deactivated enrollment
        """
        run_enrollment.deactivate_and_save(change_status, no_user=True)
        mail_api.send_course_run_unenrollment_email(run_enrollment)
        return run_enrollment

    def create_program_enrollment(
        self, existing_enrollment, to_program=None, to_user=None
    ):
        """
        Helper method to create a new ProgramEnrollment based on an existing enrollment

        Args:
            existing_enrollment (ProgramEnrollment): An existing program enrollment
            to_program (Program or None): The program to assign to the new enrollment (if None,
                the new enrollment will use the existing enrollment's program)
            to_user (User or None): The user to assign to the program enrollment (if None, the new
                enrollment will user the existing enrollment's user)
        Returns:
            tuple of (ProgramEnrollment, list(CourseRunEnrollment)): The newly created enrollments
        """
        to_user = to_user or existing_enrollment.user
        to_program = to_program or existing_enrollment.program
        enrollment_params = dict(user=to_user, program=to_program)
        enrollment_defaults = dict(
            company=existing_enrollment.company, order=existing_enrollment.order
        )
        program_enrollment, _ = create_or_update_enrollment(
            ProgramEnrollment, defaults=enrollment_defaults, **enrollment_params
        )
        existing_run_enrollments = existing_enrollment.get_run_enrollments()
        return (
            program_enrollment,
            list(
                map(
                    partial(self.create_run_enrollment, to_user=to_user),
                    existing_run_enrollments,
                )
            ),
        )

    def create_run_enrollment(self, existing_enrollment, to_run=None, to_user=None):
        """
        Helper method to create a CourseRunEnrollment based on an existing enrollment

        Args:
            existing_enrollment (CourseRunEnrollment): An existing course run enrollment
            to_run (CourseRun or None): The course run to assign to the new enrollment (if None,
                the new enrollment will use the existing enrollment's course run)
            to_user (User or None): The user to assign to the new enrollment (if None, the new
                enrollment will user the existing enrollment's user)
        Returns:
            CourseRunEnrollment: The newly created enrollment
        """
        to_user = to_user or existing_enrollment.user
        to_run = to_run or existing_enrollment.run
        enrollment_params = dict(user=to_user, run=to_run)
        enrollment_defaults = dict(
            company=existing_enrollment.company, order=existing_enrollment.order
        )
        run_enrollment, created = create_or_update_enrollment(
            CourseRunEnrollment, defaults=enrollment_defaults, **enrollment_params
        )
        self.stdout.write(
            "Course run enrollment record {}. "
            "Attempting to enroll the user {} ({}) in {} on edX...".format(
                "created" if created else "updated",
                to_user.username,
                to_user.email,
                to_run.courseware_id,
            )
        )
        enrolled_in_edx = self.enroll_in_edx(to_user, [to_run])
        if enrolled_in_edx:
            run_enrollment.edx_enrolled = True
            run_enrollment.save_and_log(None)
            mail_api.send_course_run_enrollment_email(run_enrollment)

        return run_enrollment

    def enroll_in_edx(self, user, course_runs):
        """
        Try to perform edX enrollment, but print a message and continue if it fails

        Args:
            user (User): The user to enroll
            course_runs (iterable of CourseRun): The course runs to enroll in

            :return boolean either the enrollment in edx succeeded or not.
        """
        try:
            enroll_in_edx_course_runs(user, course_runs)
            return True
        except (EdxApiEnrollErrorException, UnknownEdxApiEnrollException) as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
        return False
