"""
Management command to sync grades and certificates for a course run
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from cms.models import ExternalCoursePage
from courses.models import CourseRun
from courses.utils import ensure_course_run_grade, process_course_run_grade_certificate
from courseware.api import get_edx_grades_with_users
from mitxpro.utils import now_in_utc
from users.api import fetch_user

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command to sync grades and certificates for a course run.
    """

    help = "Sync grades and certificates for a course run for all enrolled users or a specified user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email or username of the enrolled User",
            required=False,
        )
        parser.add_argument(
            "--run",
            type=str,
            help="The 'courseware_id' value for a CourseRun",
            required=True,
        )
        parser.add_argument(
            "--grade",
            type=float,
            help="Override a grade. Setting grade to 0.0 blocks certificate creation. Setting a passing grade \
                (>0.0) allows certificate creation. Range: 0.0 - 1.0",
            required=False,
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update local grade records with results from the edX grades API",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            dest="force",
            help="Sync grades/certificates even if the given course run has not ended yet",
        )
        super().add_arguments(parser)

    def handle(  # noqa: C901, PLR0915
        self,
        *args,  # noqa: ARG002
        **options,
    ):
        """Handle command execution"""
        # Grade override for all users for the course run. Disallowed.
        if options["grade"] is not None and not options["user"]:
            raise CommandError(
                "No user supplied with override grade. Overwrite of grade is not supported for all users. Grade should only be supplied when a specific user is targeted."  # noqa: EM101
            )
        try:
            run = CourseRun.objects.get(courseware_id=options["run"])
        except CourseRun.DoesNotExist:
            raise CommandError(  # noqa: B904
                "Could not find run with courseware_id={}".format(options["run"])  # noqa: EM103
            )

        if run.course.is_external or isinstance(run.course.page, ExternalCoursePage):
            raise CommandError(
                f"Course run {run} is part of an external course. Grades and certificates cannot be synced for external courses."  # noqa: EM101
            )

        now = now_in_utc()
        if not options.get("force") and (run.end_date is None or run.end_date > now):
            raise CommandError(
                "The given course run has not yet finished, so the course grades should not be "  # noqa: EM103
                "considered final (courseware_id={}, end_date={}).\n"
                "Add the -f/--force flag if grades/certificates should be synced anyway.".format(
                    options["run"],
                    "None" if run.end_date is None else run.end_date.isoformat(),
                )
            )

        user = fetch_user(options["user"]) if options["user"] else None
        override_grade = None
        should_update = options["update"]

        if options["grade"] is not None:
            override_grade = float(options["grade"])
            if override_grade and (override_grade < 0.0 or override_grade > 1.0):
                raise CommandError("Invalid value for grade. Allowed range: 0.0 - 1.0")  # noqa: EM101

        edx_grade_user_iter = get_edx_grades_with_users(run, user=user)

        if not run.has_certificate_page:
            raise CommandError(f"Course run {run} has no certificate page.")

        results = []
        for edx_grade, user in edx_grade_user_iter:
            try:
                (
                    course_run_grade,
                    created_grade,
                    updated_grade,
                ) = ensure_course_run_grade(
                    user=user,
                    course_run=run,
                    edx_grade=edx_grade,
                    should_update=should_update,
                )

                if override_grade is not None:
                    course_run_grade.grade = override_grade
                    course_run_grade.passed = bool(override_grade)
                    course_run_grade.letter_grade = None
                    course_run_grade.set_by_admin = True
                    course_run_grade.save_and_log(None)

                _, created_cert, deleted_cert = process_course_run_grade_certificate(
                    course_run_grade=course_run_grade
                )
            except Exception as e:  # noqa: BLE001
                self.stdout.write(
                    self.style.ERROR(
                        f"Course certificate creation failed for {user} due to following reason(s),\n{e}"
                    )
                )
                continue

            if created_grade:
                grade_status = "created"
            elif updated_grade:
                grade_status = "updated"
            else:
                grade_status = "already exists"

            grade_summary = [f"passed: {course_run_grade.passed}"]
            if override_grade is not None:
                grade_summary.append(f"value override: {course_run_grade.grade}")

            if created_cert:
                cert_status = "created"
            elif deleted_cert:
                cert_status = "deleted"
            elif course_run_grade.passed:
                cert_status = "already exists"
            else:
                cert_status = "ignored"

            result_summary = "Grade: {} ({}), Certificate: {}".format(
                grade_status, ", ".join(grade_summary), cert_status
            )

            results.append(
                f"Processed {user} in course run {run.courseware_id}. Result - {result_summary}"
            )

        for result in results:
            self.stdout.write(self.style.SUCCESS(result))
