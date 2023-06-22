"""Tests for Program Certificates management command"""

import pytest
from courses.management.commands import manage_program_certificates
from courses.models import ProgramCertificate
from django.core.management.base import CommandError
from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    CourseRunGradeFactory,
    CourseRunCertificateFactory,
    CourseRunEnrollmentFactory,
    ProgramFactory,
    ProgramEnrollmentFactory,
)

pytestmark = [pytest.mark.django_db]


def test_program_certificate_management_no_argument():
    """Test that command throws error when no input is provided"""

    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle()
    assert str(command_error.value) == "Please provide a valid program readable_id."


def test_program_certificate_management_invalid_program():
    """
    Test that program certificate management command throws proper error when
    no valid program is supplied
    """

    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle(program="test")
    assert (
        str(command_error.value)
        == "Could not find course enrollment(s) with provided program readable_id=test"
    )


def test_program_certificate_creation(user):
    """
    Test that create operation for program certificate management command
    creates the program certificate for a user
    """
    program = ProgramFactory.create()
    course = CourseFactory.create(program=program)
    course_run = CourseRunFactory.create(course=course)

    CourseRunEnrollmentFactory.create(user=user, run=course_run)
    CourseRunGradeFactory.create(course_run=course_run, user=user, passed=True, grade=1)
    CourseRunCertificateFactory.create(user=user, course_run=course_run)

    manage_program_certificates.Command().handle(
        program=program.readable_id, user=user.username
    )

    generated_certificates = ProgramCertificate.objects.filter(
        user=user, program=program
    )

    assert generated_certificates.count() == 1


def test_incomplete_course_program_certificate(user):
    """
    Test that create operation for program certificate management command
    Testing program certificate creation for incomplete courses
    """
    program = ProgramFactory.create()
    courses = CourseFactory.create_batch(size=2, program=program)
    course_runs = [CourseRunFactory.create(course=course) for course in courses]

    list(
        map(
            lambda run: CourseRunEnrollmentFactory.create(user=user, run=run),
            course_runs,
        )
    )
    list(
        map(
            lambda run: CourseRunGradeFactory.create(
                course_run=run, user=user, passed=True, grade=1
            ),
            course_runs,
        )
    )

    # Generating certificate only for a single course
    CourseRunCertificateFactory.create(user=user, course_run=course_runs[0])
    manage_program_certificates.Command().handle(
        program=program.readable_id, user=user.username
    )

    generated_certificates = ProgramCertificate.objects.filter(
        user=user, program=program
    )

    assert generated_certificates.count() == 0
