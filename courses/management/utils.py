"""Utility functions/classes for course management commands"""
from django.core.management.base import BaseCommand, CommandError

from courses.models import CourseRun, CourseRunEnrollment, Program, ProgramEnrollment
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
    NoEdxApiAuthError,
)
from courseware.api import enroll_in_edx_course_runs
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
        return "<ProgramEnrollment: id={}, program={}>".format(
            enrollment.id, enrollment.program.text_id
        )
    else:
        return "<CourseRunEnrollment: id={}, run={}>".format(
            enrollment.id, enrollment.run.text_id
        )


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
    created = False
    enrollment = model_cls.all_objects.filter(**kwargs).order_by("-created_on").first()
    if not enrollment:
        enrollment = model_cls.objects.create(**{**defaults, **kwargs})
        created = True
    elif enrollment and not has_equal_properties(enrollment, defaults):
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
        program_property = command_options.get("program")
        run_property = command_options.get("run")
        order_property = command_options.get("order")
        force = command_options.get("force")

        if program_property and run_property:
            raise CommandError(
                "Either 'program' or 'run' should be provided, not both."
            )
        if not program_property and not run_property:
            raise CommandError("Either 'program' or 'run' must be provided.")

        query_params = {"user": user}
        if order_property:
            query_params["order"] = order_property

        if program_property:
            query_params["program"] = enrolled_obj = Program.objects.get(
                readable_id=program_property
            )
            enrollment = ProgramEnrollment.all_objects.filter(**query_params).first()
        else:
            query_params["run"] = enrolled_obj = CourseRun.objects.get(
                courseware_id=run_property
            )
            enrollment = CourseRunEnrollment.all_objects.filter(**query_params).first()

        if not enrollment:
            raise CommandError("Enrollment not found for: {}".format(enrolled_obj))
        if not enrollment.active and not force:
            raise CommandError(
                "The given enrollment is not active ({}).\n"
                "Add the -f/--force flag if you want to change the status anyway.".format(
                    enrollment.id
                )
            )

        return enrollment, enrolled_obj

    def create_program_enrollment(
        self,
        existing_enrollment,
        to_program=None,
        to_user=None,
        keep_failed_enrollments=False,
    ):
        """
        Helper method to create a new ProgramEnrollment based on an existing enrollment

        Args:
            existing_enrollment (ProgramEnrollment): An existing program enrollment
            to_program (Program or None): The program to assign to the new enrollment (if None,
                the new enrollment will use the existing enrollment's program)
            to_user (User or None): The user to assign to the program enrollment (if None, the new
                enrollment will user the existing enrollment's user)
            keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
                in the database even if the enrollment fails in edX.
        Returns:
            tuple of (ProgramEnrollment, list(CourseRunEnrollment)): The newly created enrollments
        """
        to_user = to_user or existing_enrollment.user
        to_program = to_program or existing_enrollment.program
        enrollment_params = dict(user=to_user, program=to_program)
        enrollment_defaults = dict(
            company=existing_enrollment.company, order=existing_enrollment.order
        )
        existing_run_enrollments = existing_enrollment.get_run_enrollments()
        created_run_enrollments = []
        for run_enrollment in existing_run_enrollments:
            created_run_enrollment = self.create_run_enrollment(
                run_enrollment,
                to_user=to_user,
                keep_failed_enrollments=keep_failed_enrollments,
            )
            if created_run_enrollment:
                created_run_enrollments.append(created_run_enrollment)

        created = False
        if created_run_enrollments:
            program_enrollment, created = create_or_update_enrollment(
                ProgramEnrollment, defaults=enrollment_defaults, **enrollment_params
            )
            return (program_enrollment, created_run_enrollments)
        else:
            if created:
                program_enrollment.delete()
            return (None, None)

    def create_run_enrollment(
        self,
        existing_enrollment,
        to_run=None,
        to_user=None,
        keep_failed_enrollments=False,
    ):
        """
        Helper method to create a CourseRunEnrollment based on an existing enrollment

        Args:
            existing_enrollment (CourseRunEnrollment): An existing course run enrollment
            to_run (CourseRun or None): The course run to assign to the new enrollment (if None,
                the new enrollment will use the existing enrollment's course run)
            to_user (User or None): The user to assign to the new enrollment (if None, the new
                enrollment will user the existing enrollment's user)
            keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
                in the database even if the enrollment fails in edX.
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
        elif not keep_failed_enrollments:
            if created:
                run_enrollment.delete()
            return None

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
        except (
            EdxApiEnrollErrorException,
            UnknownEdxApiEnrollException,
            NoEdxApiAuthError,
        ) as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
        return False
