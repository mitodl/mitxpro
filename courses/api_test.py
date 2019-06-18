"""Courses API tests"""
import pytest
import factory

from courses.api import get_user_enrollments
from courses.factories import (
    ProgramFactory,
    CourseRunFactory,
    CourseRunEnrollmentFactory,
    ProgramEnrollmentFactory,
)

# pylint: disable=redefined-outer-name


@pytest.mark.django_db
def test_get_user_enrollments(user):
    """Test that get_user_enrollments returns an object with a user's program and course enrollments"""
    program = ProgramFactory.create()
    program_course_runs = CourseRunFactory.create_batch(3, course__program=program)
    non_program_course_runs = CourseRunFactory.create_batch(2, course__program=None)
    all_course_runs = program_course_runs + non_program_course_runs
    course_run_enrollments = CourseRunEnrollmentFactory.create_batch(
        len(all_course_runs), run=factory.Iterator(all_course_runs), user=user
    )
    program_enrollment = ProgramEnrollmentFactory.create(program=program, user=user)
    # Add a non-active enrollment so we can confirm that it isn't returned
    CourseRunEnrollmentFactory.create(user=user, active=False)

    def key_func(_run):
        """ Function for sorting runs by id"""
        return _run.id

    user_enrollments = get_user_enrollments(user)
    assert list(user_enrollments.programs) == [program_enrollment]
    assert sorted(list(user_enrollments.program_runs), key=key_func) == sorted(
        [
            run_enrollment
            for run_enrollment in course_run_enrollments
            if run_enrollment.run in program_course_runs
        ],
        key=key_func,
    )
    assert sorted(list(user_enrollments.non_program_runs), key=key_func) == sorted(
        [
            run_enrollment
            for run_enrollment in course_run_enrollments
            if run_enrollment.run in non_program_course_runs
        ],
        key=key_func,
    )
