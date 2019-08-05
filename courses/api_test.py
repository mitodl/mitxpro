"""Courses API tests"""
from datetime import timedelta

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
from mitxpro.utils import now_in_utc


@pytest.mark.django_db
def test_get_user_enrollments(user):
    """Test that get_user_enrollments returns an object with a user's program and course enrollments"""
    past_date = now_in_utc() - timedelta(days=1)
    program = ProgramFactory.create()
    past_program = ProgramFactory.create()

    program_course_runs = CourseRunFactory.create_batch(3, course__program=program)
    past_program_course_runs = CourseRunFactory.create_batch(
        3, end_date=past_date, course__program=past_program
    )
    non_program_course_runs = CourseRunFactory.create_batch(2, course__program=None)
    past_non_program_course_runs = CourseRunFactory.create_batch(
        2, end_date=past_date, course__program=None
    )
    all_course_runs = (
        program_course_runs
        + past_program_course_runs
        + non_program_course_runs
        + past_non_program_course_runs
    )
    course_run_enrollments = CourseRunEnrollmentFactory.create_batch(
        len(all_course_runs), run=factory.Iterator(all_course_runs), user=user
    )
    program_enrollment = ProgramEnrollmentFactory.create(program=program, user=user)
    past_program_enrollment = ProgramEnrollmentFactory.create(
        program=past_program, user=user
    )
    # Add a non-active enrollment so we can confirm that it isn't returned
    CourseRunEnrollmentFactory.create(user=user, active=False)

    def key_func(_run):
        """ Function for sorting runs by id"""
        return _run.id

    user_enrollments = get_user_enrollments(user)
    assert list(user_enrollments.programs) == [program_enrollment]
    assert list(user_enrollments.past_programs) == [past_program_enrollment]
    assert sorted(list(user_enrollments.program_runs), key=key_func) == sorted(
        [
            run_enrollment
            for run_enrollment in course_run_enrollments
            if run_enrollment.run in program_course_runs + past_program_course_runs
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

    assert sorted(list(user_enrollments.past_non_program_runs), key=key_func) == sorted(
        [
            run_enrollment
            for run_enrollment in course_run_enrollments
            if run_enrollment.run in past_non_program_course_runs
        ],
        key=key_func,
    )
