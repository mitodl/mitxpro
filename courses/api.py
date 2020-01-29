"""API for the Courses app"""

import itertools
from collections import namedtuple
from functools import partial
import logging

from courses.models import CourseRunEnrollment, ProgramEnrollment
from courseware.api import unenroll_edx_course_run
from ecommerce import mail_api
from mitxpro.utils import partition

log = logging.getLogger(__name__)
UserEnrollments = namedtuple(
    "UserEnrollments",
    [
        "programs",
        "past_programs",
        "program_runs",
        "non_program_runs",
        "past_non_program_runs",
    ],
)


def get_user_enrollments(user):
    """
    Fetches a user's enrollments

    Args:
        user (User): A user
    Returns:
        UserEnrollments: An object representing a user's program and course run enrollments
    """
    program_enrollments = (
        ProgramEnrollment.objects.select_related("program__programpage")
        .prefetch_related("program__courses")
        .select_related("user", "company")
        .filter(user=user)
        .all()
    )
    program_courses = itertools.chain(
        *(
            program_enrollment.program.courses.all()
            for program_enrollment in program_enrollments
        )
    )
    program_course_ids = set(course.id for course in program_courses)
    course_run_enrollments = (
        CourseRunEnrollment.objects.select_related("run__course__coursepage", "company")
        .filter(user=user)
        .order_by("run__start_date")
        .all()
    )
    non_program_run_enrollments, program_run_enrollments = partition(
        course_run_enrollments,
        lambda course_run_enrollment: (
            course_run_enrollment.run.course_id in program_course_ids
        ),
    )
    program_enrollments, past_program_enrollments = partition(
        program_enrollments, lambda program_enrollment: program_enrollment.is_ended
    )
    non_program_run_enrollments, past_non_program_run_enrollments = partition(
        non_program_run_enrollments,
        lambda non_program_run_enrollment: non_program_run_enrollment.is_ended,
    )

    return UserEnrollments(
        programs=program_enrollments,
        past_programs=past_program_enrollments,
        program_runs=program_run_enrollments,
        non_program_runs=non_program_run_enrollments,
        past_non_program_runs=past_non_program_run_enrollments,
    )


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
    try:
        unenroll_edx_course_run(run_enrollment)
    except Exception:  # pylint: disable=broad-except
        log.exception(
            "Failed to unenroll course run '%s' for user '%s' in edX",
            run_enrollment.run.courseware_id,
            run_enrollment.user.email,
        )
    else:
        mail_api.send_course_run_unenrollment_email(run_enrollment)
    return run_enrollment


def deactivate_program_enrollment(
    program_enrollment, change_status, limit_to_order=True
):
    """
    Helper method to deactivate a ProgramEnrollment

    Args:
        program_enrollment (ProgramEnrollment): The program enrollment to deactivate
        change_status (str): The change status to set on the enrollment when deactivating
        limit_to_order (bool): If True, only deactivate enrollments associated with the
            same Order that the program enrollment is associated with

    Returns:
        tuple of ProgramEnrollment, list(CourseRunEnrollment): The deactivated enrollments
    """
    program_enrollment.deactivate_and_save(change_status, no_user=True)
    run_enrollment_params = (
        dict(order_id=program_enrollment.order_id)
        if limit_to_order and program_enrollment.order_id
        else {}
    )
    program_run_enrollments = program_enrollment.get_run_enrollments(
        **run_enrollment_params
    )
    return (
        program_enrollment,
        list(
            map(
                partial(deactivate_run_enrollment, change_status=change_status),
                program_run_enrollments,
            )
        ),
    )
