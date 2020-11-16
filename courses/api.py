"""API for the Courses app"""

import itertools
from collections import namedtuple
import logging
from traceback import format_exc

from django.core.exceptions import ValidationError

from courses.constants import ENROLL_CHANGE_STATUS_DEFERRED
from courses.models import CourseRunEnrollment, ProgramEnrollment, CourseRun
from courseware.api import unenroll_edx_course_run, enroll_in_edx_course_runs
from courseware.exceptions import (
    UnknownEdxApiEnrollException,
    EdxApiEnrollErrorException,
    NoEdxApiAuthError,
)
from ecommerce import mail_api
from mitxpro.utils import partition, first_or_none

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


def create_run_enrollments(
    user, runs, keep_failed_enrollments=False, order=None, company=None
):
    """
    Creates local records of a user's enrollment in course runs, and attempts to enroll them
    in edX via API

    Args:
        user (User): The user to enroll
        runs (iterable of CourseRun): The course runs to enroll in
        order (ecommerce.models.Order or None): The order associated with these enrollments
        company (ecommerce.models.Company or None): The company on whose behalf these enrollments
            are being created
        keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
            in the database even if the enrollment fails in edX.

    Returns:
        (list of CourseRunEnrollment, bool): A list of enrollment objects that were successfully
            created, paired with a boolean indicating whether or not edX enrollment was successful
            for all of the given course runs
    """
    successful_enrollments = []

    try:
        enroll_in_edx_course_runs(user, runs)
    except (
        EdxApiEnrollErrorException,
        UnknownEdxApiEnrollException,
        NoEdxApiAuthError,
    ):
        log.exception(
            "edX enrollment failure for user: %s, runs: %s (order: %s)",
            user,
            [run.courseware_id for run in runs],
            order.id if order else None,
        )
        edx_request_success = False
        if not keep_failed_enrollments:
            return successful_enrollments, edx_request_success
    else:
        edx_request_success = True

    for run in runs:
        try:
            enrollment, created = CourseRunEnrollment.all_objects.get_or_create(
                user=user,
                run=run,
                order=order,
                defaults=dict(company=company, edx_enrolled=edx_request_success),
            )
            if not created and not enrollment.active:
                enrollment.edx_enrolled = edx_request_success
                enrollment.reactivate_and_save()
        except:  # pylint: disable=bare-except
            mail_api.send_enrollment_failure_message(order, run, details=format_exc())
            log.exception(
                "Failed to create/update enrollment record (user: %s, run: %s, order: %s)",
                user,
                run.courseware_id,
                order.id if order else None,
            )
        else:
            successful_enrollments.append(enrollment)
            if enrollment.edx_enrolled:
                mail_api.send_course_run_enrollment_email(enrollment)
    return successful_enrollments, edx_request_success


def create_program_enrollments(user, programs, order=None, company=None):
    """
    Creates local records of a user's enrollment in programs

    Args:
        user (User): The user to enroll
        programs (iterable of Program): The course runs to enroll in
        order (ecommerce.models.Order or None): The order associated with these enrollments
        company (ecommerce.models.Company or None): The company on whose behalf these enrollments
            are being created

    Returns:
        list of ProgramEnrollment: A list of enrollment objects that were successfully created
    """
    successful_enrollments = []
    for program in programs:
        try:
            enrollment, created = ProgramEnrollment.all_objects.get_or_create(
                user=user, program=program, order=order, defaults=dict(company=company)
            )
            if not created and not enrollment.active:
                enrollment.reactivate_and_save()
        except:  # pylint: disable=bare-except
            mail_api.send_enrollment_failure_message(
                order, program, details=format_exc()
            )
            log.exception(
                "Failed to create/update enrollment record (user: %s, program: %s, order: %s)",
                user,
                program.readable_id,
                order.id if order else None,
            )
        else:
            successful_enrollments.append(enrollment)
    return successful_enrollments


def deactivate_run_enrollment(
    run_enrollment, change_status, keep_failed_enrollments=False
):
    """
    Helper method to deactivate a CourseRunEnrollment

    Args:
        run_enrollment (CourseRunEnrollment): The course run enrollment to deactivate
        change_status (str): The change status to set on the enrollment when deactivating
        keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
            in the database even if the enrollment fails in edX.

    Returns:
        CourseRunEnrollment: The deactivated enrollment
    """
    try:
        unenroll_edx_course_run(run_enrollment)
    except Exception:  # pylint: disable=broad-except
        log.exception(
            "Failed to unenroll course run '%s' for user '%s' in edX",
            run_enrollment.run.courseware_id,
            run_enrollment.user.email,
        )
        if not keep_failed_enrollments:
            return None
        edx_unenrolled = False
    else:
        edx_unenrolled = True
        mail_api.send_course_run_unenrollment_email(run_enrollment)
    if edx_unenrolled:
        run_enrollment.edx_enrolled = False
    run_enrollment.deactivate_and_save(change_status, no_user=True)
    return run_enrollment


def deactivate_program_enrollment(
    program_enrollment,
    change_status,
    keep_failed_enrollments=False,
    limit_to_order=True,
):
    """
    Helper method to deactivate a ProgramEnrollment

    Args:
        program_enrollment (ProgramEnrollment): The program enrollment to deactivate
        change_status (str): The change status to set on the enrollment when deactivating
        keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
            in the database even if the enrollment fails in edX.
        limit_to_order (bool): If True, only deactivate enrollments associated with the
            same Order that the program enrollment is associated with

    Returns:
        tuple of ProgramEnrollment, list(CourseRunEnrollment): The deactivated enrollments
    """
    run_enrollment_params = (
        dict(order_id=program_enrollment.order_id)
        if limit_to_order and program_enrollment.order_id
        else {}
    )
    program_run_enrollments = program_enrollment.get_run_enrollments(
        **run_enrollment_params
    )

    deactivated_course_runs = []
    for run_enrollment in program_run_enrollments:
        if deactivate_run_enrollment(
            run_enrollment,
            change_status=change_status,
            keep_failed_enrollments=keep_failed_enrollments,
        ):
            deactivated_course_runs.append(run_enrollment)

    if deactivated_course_runs:
        program_enrollment.deactivate_and_save(change_status, no_user=True)
    else:
        return None, None

    return program_enrollment, deactivated_course_runs


def defer_enrollment(
    user,
    from_courseware_id,
    to_courseware_id,
    keep_failed_enrollments=False,
    force=False,
):
    """
    Deactivates a user's existing enrollment in one course run and enrolls the user in another.

    Args:
        user (User): The enrolled user
        from_courseware_id (str): The courseware_id value of the currently enrolled CourseRun
        to_courseware_id (str): The courseware_id value of the desired CourseRun
        keep_failed_enrollments: (boolean): If True, keeps the local enrollment record
            in the database even if the enrollment fails in edX.
        force (bool): If True, the deferral will be completed even if the current enrollment is inactive
            or the desired enrollment is in a different course

    Returns:
        (CourseRunEnrollment, CourseRunEnrollment): The deactivated enrollment paired with the
            new enrollment that was the target of the deferral
    """
    from_enrollment = CourseRunEnrollment.all_objects.get(
        user=user, run__courseware_id=from_courseware_id
    )
    if not force and not from_enrollment.active:
        raise ValidationError(
            "Cannot defer from inactive enrollment (id: {}, run: {}, user: {}). "
            "Set force=True to defer anyway.".format(
                from_enrollment.id, from_enrollment.run.courseware_id, user.email
            )
        )
    to_run = CourseRun.objects.get(courseware_id=to_courseware_id)
    if from_enrollment.run == to_run:
        raise ValidationError(
            "Cannot defer to the same course run (run: {})".format(to_run.courseware_id)
        )
    elif not to_run.is_not_beyond_enrollment:
        raise ValidationError(
            "Cannot defer to a course run that is outside of its enrollment period (run: {}).".format(
                to_run.courseware_id
            )
        )
    elif not force and from_enrollment.run.course != to_run.course:
        raise ValidationError(
            "Cannot defer to a course run of a different course ('{}' -> '{}'). "
            "Set force=True to defer anyway.".format(
                from_enrollment.run.course.title, to_run.course.title
            )
        )
    to_enrollments, _ = create_run_enrollments(
        user,
        [to_run],
        order=from_enrollment.order,
        company=from_enrollment.company,
        keep_failed_enrollments=keep_failed_enrollments,
    )
    from_enrollment = deactivate_run_enrollment(
        from_enrollment,
        ENROLL_CHANGE_STATUS_DEFERRED,
        keep_failed_enrollments=keep_failed_enrollments,
    )
    return from_enrollment, first_or_none(to_enrollments)
