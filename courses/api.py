"""API for the Courses app"""

import itertools
from collections import namedtuple

from courses.models import CourseRunEnrollment, ProgramEnrollment
from mitxpro.utils import partition


UserEnrollments = namedtuple(
    "UserEnrollments", ["programs", "program_runs", "non_program_runs"]
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
        CourseRunEnrollment.objects.select_related("run__course__coursepage")
        .filter(user=user)
        .all()
    )
    non_program_run_enrollments, program_run_enrollments = partition(
        course_run_enrollments,
        lambda course_run_enrollment: (
            course_run_enrollment.run.course_id in program_course_ids
        ),
    )
    return UserEnrollments(
        programs=program_enrollments,
        program_runs=program_run_enrollments,
        non_program_runs=non_program_run_enrollments,
    )
