"""Tests for command utils"""

from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

from courses.factories import (
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramEnrollmentFactory,
)
from courses.management import utils
from courses.management.utils import (
    EnrollmentChangeCommand,
    create_or_update_enrollment,
    enrollment_summaries,
    enrollment_summary,
)
from courses.models import CourseRunEnrollment
from users.factories import UserFactory
from ecommerce import mail_api

User = get_user_model()

pytestmark = [pytest.mark.django_db]


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


@pytest.mark.parametrize("command_options", [{"program": "fake", "run": "fake"}, {}])
def test_fetch_enrollment_parameters(command_options):
    """Test that fetch_enrollment raises errors on wrong parameters combination"""
    user = UserFactory()
    with pytest.raises(CommandError):
        EnrollmentChangeCommand.fetch_enrollment(user, command_options)


def test_fetch_enrollment_inactive():
    """Test that fetch_enrollment raises an error on inactive enrollment"""
    enrollment = CourseRunEnrollmentFactory(active=False)
    with pytest.raises(CommandError):
        EnrollmentChangeCommand.fetch_enrollment(
            enrollment.user, {"run": enrollment.run.courseware_id}
        )


def test_create_run_enrollment():
    """Test that the EnrollmentChangeCommand helper method works properly"""
    user = UserFactory()
    user_2 = UserFactory()
    enrollment = CourseRunEnrollmentFactory(user=user, edx_enrolled=False)

    assert enrollment.edx_enrolled is False

    with patch.object(utils, "enroll_in_edx_course_runs"):
        with patch.object(
            mail_api, "send_course_run_enrollment_email"
        ) as mock_send_email:
            command = EnrollmentChangeCommand()
            enrollment_2 = command.create_run_enrollment(enrollment, to_user=user_2)
            mock_send_email.assert_called()

    assert enrollment_2.active is True
    assert enrollment_2.edx_enrolled is True
    assert enrollment_2.user == user_2
    assert enrollment_2.run == enrollment.run

    enrollment_3 = command.create_run_enrollment(enrollment_2, to_user=UserFactory())
    assert enrollment_3.active is True
    assert enrollment_3.edx_enrolled is False


def test_create_program_enrollment():
    """Test that the EnrollmentChangeCommand helper method works as expected for program enrollments"""
    user = UserFactory()
    user_2 = UserFactory()
    program_enrollment = ProgramEnrollmentFactory(user=user)
    CourseRunEnrollmentFactory(
        run__course__program=program_enrollment.program, user=user
    )
    CourseRunEnrollmentFactory(
        run__course__program=program_enrollment.program, user=user
    )

    with patch.object(utils, "enroll_in_edx_course_runs"):
        with patch.object(
            mail_api, "send_course_run_enrollment_email"
        ) as mock_send_email:
            command = EnrollmentChangeCommand()
            program_enrollment_2, course_run_enrollments_2 = command.create_program_enrollment(
                program_enrollment, to_user=user_2
            )
            mock_send_email.assert_called()
            assert len(course_run_enrollments_2) == 2
            for enrollment in course_run_enrollments_2:
                assert enrollment.active is True
                assert enrollment.edx_enrolled is True
                assert enrollment.user == user_2

    assert program_enrollment_2.user == user_2
    assert program_enrollment_2.program == program_enrollment.program


def test_enrollment_summary():
    """Test that the enrollment_summary works as expected"""
    course_enrollment = CourseRunEnrollmentFactory()
    program_enrollment = ProgramEnrollmentFactory()

    assert (
        enrollment_summary(course_enrollment)
        == f"<CourseRunEnrollment: id={course_enrollment.id}, run={course_enrollment.run.text_id}>"
    )
    assert (
        enrollment_summary(program_enrollment)
        == f"<ProgramEnrollment: id={program_enrollment.id}, program={program_enrollment.program.text_id}>"
    )


def test_enrollment_summaries():
    """Test that the enrollment_summaries method works as expected"""
    enrollments = [CourseRunEnrollmentFactory(), ProgramEnrollmentFactory()]

    summaries = enrollment_summaries(enrollments)

    assert (
        summaries[0]
        == f"<CourseRunEnrollment: id={enrollments[0].id}, run={enrollments[0].run.text_id}>"
    )
    assert (
        summaries[1]
        == f"<ProgramEnrollment: id={enrollments[1].id}, program={enrollments[1].program.text_id}>"
    )


def test_create_or_update_enrollment():
    """Test that the create_or_update_enrollment method is as per specs"""
    user = UserFactory()
    run = CourseRunFactory()

    enrollment, created = create_or_update_enrollment(
        CourseRunEnrollment, user=user, run=run
    )
    assert created is True
    assert enrollment.active is True
    assert enrollment.run.text_id == run.text_id

    enrollment_2, created_2 = create_or_update_enrollment(
        CourseRunEnrollment, user=user, run=run, defaults={"edx_enrolled": True}
    )
    assert created_2 is False
    assert enrollment_2.edx_enrolled is True
    assert enrollment_2 == enrollment
