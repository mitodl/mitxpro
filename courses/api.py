"""API for the Courses app"""

import itertools
from collections import namedtuple

from courses.models import CourseRunEnrollment, ProgramEnrollment
from mitxpro.utils import partition

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
