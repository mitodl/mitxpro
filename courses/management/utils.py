"""Utility functions/classes for course management commands"""

from dataclasses import dataclass
from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from courses.models import CourseRun, CourseRunEnrollment, Program, ProgramEnrollment
from courseware.api import enroll_in_edx_course_runs
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    NoEdxApiAuthError,
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
        return f"<ProgramEnrollment: id={enrollment.id}, program={enrollment.program.text_id}>"
    else:
        return (
            f"<CourseRunEnrollment: id={enrollment.id}, run={enrollment.run.text_id}>"
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
                "Either 'program' or 'run' should be provided, not both."  # noqa: EM101
            )
        if not program_property and not run_property:
            raise CommandError("Either 'program' or 'run' must be provided.")  # noqa: EM101

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
            raise CommandError(f"Enrollment not found for: {enrolled_obj}")  # noqa: EM102
        if not enrollment.active and not force:
            raise CommandError(
                "The given enrollment is not active ({}).\n"  # noqa: EM103, UP032, RUF100
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
        keep_failed_enrollments=False,  # noqa: FBT002
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
        enrollment_params = dict(user=to_user, program=to_program)  # noqa: C408
        enrollment_defaults = dict(  # noqa: C408
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
        keep_failed_enrollments=False,  # noqa: FBT002
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
        enrollment_params = dict(user=to_user, run=to_run)  # noqa: C408
        enrollment_defaults = dict(  # noqa: C408
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
            mail_api.send_course_run_enrollment_welcome_email(run_enrollment)
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
            return True  # noqa: TRY300
        except (
            EdxApiEnrollErrorException,
            UnknownEdxApiEnrollException,
            NoEdxApiAuthError,
        ) as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
        return False


@dataclass
class CourseInfo:
    """
    Data class for course information with named fields
    """

    code: str
    title: Optional[str] = None
    msg: Optional[str] = None


class StatCategory:
    """Represents a category of statistics with its display information"""

    def __init__(self, key, display_name=None, label=None):
        """
        Initialize a stat category

        Args:
            key: The dictionary key for this stat
            display_name: Human-readable category name
            label: Description of the items
        """
        self.key = key
        self.display_name = display_name or self._generate_display_name(key)
        self.label = label or self._generate_label(key)
        self.items = []

    def _generate_display_name(self, key):
        """Generate a display name from the key"""
        return " ".join(word.capitalize() for word in key.split("_"))

    def _generate_label(self, key):
        """Generate a label based on the key"""
        if "course" in key and "run" not in key:
            return "External Course Codes"
        elif "run" in key:
            return "External Course Run Codes"
        elif "product" in key:
            return "Course Run courseware_ids"
        elif "certificate" in key:
            return "Course Readable IDs"
        else:
            return "Items"

    def add(self, code, title=None, msg=None):
        """Add an item to this stat category"""
        self.items.append(CourseInfo(code=code, title=title, msg=msg))

    def get_codes(self):
        """Get the set of unique codes in this category"""
        return {item.code for item in self.items if item.code is not None}

    def __len__(self):
        """Return the number of items in this category"""
        return len(self.items)


class StatsCollector:
    """Collector for external course sync statistics with named properties"""

    def __init__(self):
        self.categories = {
            "courses_created": StatCategory("courses_created"),
            "existing_courses": StatCategory("existing_courses"),
            "course_runs_created": StatCategory("course_runs_created"),
            "course_runs_updated": StatCategory("course_runs_updated"),
            "course_runs_without_prices": StatCategory("course_runs_without_prices"),
            "course_runs_skipped": StatCategory(
                "course_runs_skipped",
                display_name="Course Runs Skipped due to bad data",
            ),
            "course_runs_expired": StatCategory(
                "course_runs_deactivated", display_name="Expired Course Runs"
            ),
            "course_runs_deactivated": StatCategory("course_runs_deactivated"),
            "course_pages_created": StatCategory("course_pages_created"),
            "course_pages_updated": StatCategory("course_pages_updated"),
            "products_created": StatCategory("products_created"),
            "product_versions_created": StatCategory("product_versions_created"),
            "certificates_created": StatCategory(
                "certificates_created", display_name="Certificate Pages Created"
            ),
            "certificates_updated": StatCategory(
                "certificates_updated", display_name="Certificate Pages Updated"
            ),
        }

    def add_stat(self, key, code, title=None, msg=None):
        """
        Add an item to a specific stat category
        """
        if key in self.categories:
            existing_item = [
                item for item in self.categories[key].items if item.code == code
            ]
            if not existing_item:
                self.categories[key].add(code, title, msg)

    def add_bulk(self, key, codes):
        """
        Add multiple items within the same category
        """
        if key in self.categories:
            for code in codes:
                self.add_stat(key, code)

    def remove_duplicates(self, source_key, items_to_remove_key):
        """
        Remove items from one category that exist in another category
        """
        if (
            source_key not in self.categories
            or items_to_remove_key not in self.categories
        ):
            return

        codes_to_remove = {
            item.code for item in self.categories[items_to_remove_key].items
        }

        self.categories[source_key].items = [
            item
            for item in self.categories[source_key].items
            if item.code not in codes_to_remove
        ]

    def log_stats(self, logger):
        """
        Log all collected statistics
        """
        for category in self.categories.values():
            codes = category.get_codes()
            logger.log_style_success(
                f"Number of {category.display_name}: {len(codes)}."
            )
            logger.log_style_success(f"{category.label}: {codes or 0}\n")

    def email_stats(self):
        """
        Return statistics formatted for email template"
        """
        return {key: category.items for key, category in self.categories.items()}
