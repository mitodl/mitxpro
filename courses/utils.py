"""
Utilities for courses/certificates
"""
import logging
from requests.exceptions import HTTPError
from rest_framework.status import HTTP_404_NOT_FOUND
from django.conf import settings
from django.db import transaction

from courses.constants import PROGRAM_TEXT_ID_PREFIX
from courses.models import (
    CourseRunGrade,
    CourseRunCertificate,
    ProgramCertificate,
    Program,
    CourseRun,
    ProgramEnrollment,
)
from mitxpro.utils import has_equal_properties
from courseware.api import get_edx_api_course_detail_client


log = logging.getLogger(__name__)


def ensure_course_run_grade(user, course_run, edx_grade, should_update=False):
    """
    Ensure that the local grades repository has the grade for the User/CourseRun combination supplied.

    Args:
        user (user.models.User): The user for whom the grade is being synced
        course_run (courses.models.CourseRun): The course run for which the grade is created
        edx_grade (edx_api.grades.models.UserCurrentGrade): The OpenEdx grade object
        should_update (bool): Update the local grade record if it exists

    Returns:
        (courses.models.CourseRunGrade, bool, bool) that depicts the CourseRunGrade, created and updated values
    """
    grade_properties = {
        "grade": edx_grade.percent,
        "passed": edx_grade.passed,
        "letter_grade": edx_grade.letter_grade,
    }

    updated = False
    if should_update:
        with transaction.atomic():
            run_grade, created = CourseRunGrade.objects.select_for_update().get_or_create(
                course_run=course_run, user=user, defaults=grade_properties
            )

            if (
                not created
                and not run_grade.set_by_admin
                and not has_equal_properties(run_grade, grade_properties)
            ):
                # Perform actual update now.
                run_grade.grade = edx_grade.percent
                run_grade.passed = edx_grade.passed
                run_grade.letter_grade = edx_grade.letter_grade
                run_grade.save_and_log(None)
                updated = True

    else:
        run_grade, created = CourseRunGrade.objects.get_or_create(
            course_run=course_run, user=user, defaults=grade_properties
        )
    return run_grade, created, updated


def process_course_run_grade_certificate(course_run_grade):
    """
    Ensure that the couse run certificate is in line with the values in the course run grade

    Args:
        course_run_grade (courses.models.CourseRunGrade): The course run grade for which to generate/delete the certificate

    Returns:
        (courses.models.CourseRunCertificate, bool, bool) that depicts the CourseRunCertificate, created, deleted values
    """
    user = course_run_grade.user
    course_run = course_run_grade.course_run

    # A grade of 0.0 indicates that the certificate should be deleted
    should_delete = not bool(course_run_grade.grade)
    should_create = course_run_grade.passed

    if should_delete:
        delete_count, _ = CourseRunCertificate.objects.filter(
            user=user, course_run=course_run
        ).delete()
        return None, False, (delete_count > 0)
    elif should_create:
        certificate, created = CourseRunCertificate.objects.get_or_create(
            user=user, course_run=course_run
        )
        return certificate, created, False
    return None, False, False


def generate_program_certificate(user, program):
    """
    Create a program certificate if the user has a course certificate
    for each course in the program. Also, It will create the
    program enrollment if it does not exist for the user.

    Args:
        user (User): a Django user.
        program (programs.models.Program): program where the user is enrolled.

    Returns:
        (ProgramCertificate or None, bool): A tuple containing a
        ProgramCertificate (or None if one was not found or created) paired
        with a boolean indicating whether the certificate was newly created.
    """
    existing_cert_queryset = ProgramCertificate.objects.filter(
        user=user, program=program
    )
    if existing_cert_queryset.exists():
        ProgramEnrollment.objects.get_or_create(
            program=program, user=user, defaults={"active": True, "change_status": None}
        )
        return existing_cert_queryset.first(), False

    courses_in_program_ids = set(program.courses.values_list("id", flat=True))
    num_courses_with_cert = (
        CourseRunCertificate.objects.filter(
            user=user, course_run__course_id__in=courses_in_program_ids
        )
        .distinct()
        .count()
    )

    if len(courses_in_program_ids) > num_courses_with_cert:
        return None, False

    program_cert = ProgramCertificate.objects.create(user=user, program=program)
    if program_cert:
        log.info(
            "Program certificate for [%s] in program [%s] is created.",
            user.username,
            program.title,
        )
        _, created = ProgramEnrollment.objects.get_or_create(
            program=program, user=user, defaults={"active": True, "change_status": None}
        )

        if created:
            log.info(
                "Program enrollment for [%s] in program [%s] is created.",
                user.username,
                program.title,
            )

    return program_cert, True


def revoke_program_certificate(
    user, readable_id, revoke_state, include_program_courses
):
    """
    Revoked a program certificate.

    Args:
        user (User): a Django user.
        readable_id: represents the program (readable_id) for revoking a ProgramCertificate.
        revoke_state: (bool) override the is_revoked state of ProgramCertificate.
        include_program_courses: (bool) Indicate to revoke/un-revoke all course runs that are associated with a program.
    """
    program = Program.objects.get(readable_id=readable_id)
    try:
        program_certificate = ProgramCertificate.all_objects.get(
            user=user, program__readable_id=readable_id
        )
    except ProgramCertificate.DoesNotExist:
        log.warning(
            "Program certificate for user: %s in program %s does not exist.",
            user.username,
            readable_id,
        )
        return False

    program_certificate.is_revoked = revoke_state
    program_certificate.save()

    if include_program_courses:
        courses_in_program_ids = set(program.courses.values_list("id", flat=True))
        CourseRunCertificate.all_objects.filter(
            user=user, course_run__course_id__in=courses_in_program_ids
        ).update(is_revoked=revoke_state)

        log.info(
            "Course certificates associated with that program: [%s] are also updated",
            program,
        )

    return True


def revoke_course_run_certificate(user, courseware_id, revoke_state):
    """
        Revoked a course run certificate.

        Args:
            user (User): a Django user.
            courseware_id: represents the course run.
            revoke_state: represents the course run (courseware_id) for revoking a CourseRunCertificate.
    """
    course_run = CourseRun.objects.get(courseware_id=courseware_id)
    try:
        course_run_certificate = CourseRunCertificate.all_objects.get(
            user=user, course_run=course_run
        )
    except CourseRunCertificate.DoesNotExist:
        log.warning(
            "Course run certificate for user: %s and course_run: %s does not exist.",
            user.username,
            course_run,
        )
        return False

    course_run_certificate.is_revoked = revoke_state
    course_run_certificate.save()

    return True


def sync_course_runs(runs):
    """
    Sync course run dates and title from Open edX

    Args:
        runs ([CourseRun]): list of CourseRun objects.

    Returns:
        [str], [str]: Lists of success and error logs respectively
    """
    api_client = get_edx_api_course_detail_client()

    success_count = 0
    failure_count = 0

    # Iterate all eligible runs and sync if possible
    for run in runs:
        try:
            course_detail = api_client.get_detail(
                course_id=run.courseware_id,
                username=settings.OPENEDX_SERVICE_WORKER_USERNAME,
            )
        except HTTPError as e:
            failure_count += 1
            if e.response.status_code == HTTP_404_NOT_FOUND:
                log.error(
                    "Course not found on edX for readable id: %s", run.courseware_id
                )
            else:
                log.error("%s: %s", str(e), run.courseware_id)
        except Exception as e:  # pylint: disable=broad-except
            failure_count += 1
            log.error("%s: %s", str(e), run.courseware_id)
        else:
            # Reset the expiration_date so it is calculated automatically and
            # does not raise a validation error now that the start or end date
            # has changed.
            if (
                run.start_date != course_detail.start
                or run.end_date != course_detail.end
            ):
                run.expiration_date = None

            run.title = course_detail.name
            run.start_date = course_detail.start
            run.end_date = course_detail.end
            run.enrollment_start = course_detail.enrollment_start
            run.enrollment_end = course_detail.enrollment_end
            try:
                run.save()
                success_count += 1
                log.info("Updated course run: %s", run.courseware_id)
            except Exception as e:  # pylint: disable=broad-except
                # Report any validation or otherwise model errors
                log.error("%s: %s", str(e), run.courseware_id)
                failure_count += 1

    return success_count, failure_count


def is_program_text_id(item_text_id):
    """
    Analyzes a text id for some enrollable item and returns True if it's a program id

    Args:
        item_text_id (str): The text id for some enrollable item (program/course run)

    Returns:
        bool: True if the given id is a program id
    """
    return item_text_id.startswith(PROGRAM_TEXT_ID_PREFIX)
