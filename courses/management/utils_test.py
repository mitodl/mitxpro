"""Tests for command utils"""

import pytest
from django.contrib.auth import get_user_model

from courses.factories import CourseRunEnrollmentFactory, ProgramEnrollmentFactory
from courses.management.utils import EnrollmentChangeCommand
from users.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize("order", [True, False])
def test_fetch_enrollment(order):
    """Test that method return enrollment and enrolled object, include order while querying if passed"""
    user = UserFactory()
    run_enrollment = CourseRunEnrollmentFactory(user=user)
    program_enrollment = ProgramEnrollmentFactory(user=user)

    run_command_options = {"run": run_enrollment.run.courseware_id}
    program_command_options = {"program": program_enrollment.program.readable_id}

    if order:
        run_command_options["order"] = run_enrollment.order
        program_command_options["order"] = program_enrollment.order
    enrollment_obj, enrolled_obj = EnrollmentChangeCommand.fetch_enrollment(
        user=user, command_options=run_command_options
    )

    assert enrolled_obj == run_enrollment.run
    assert enrollment_obj == run_enrollment

    enrollment_obj, enrolled_obj = EnrollmentChangeCommand.fetch_enrollment(
        user=user, command_options=program_command_options
    )

    assert enrolled_obj == program_enrollment.program
    assert enrollment_obj == program_enrollment
