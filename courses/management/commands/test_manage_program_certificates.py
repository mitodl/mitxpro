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
        manage_program_certificates.Command().handle(readable_id="test")
    assert (
        str(command_error.value)
        == "Could not find program enrollment(s) with readable_id=test"
    )


def test_program_certificate_creation(user):
    """
    Test that create operation for program certificate management command
    creates the program certificate for a user
    """
    program = ProgramFactory.create()
    ProgramEnrollmentFactory.create(user=user, program=program)
    course = CourseFactory.create(program=program)
    course_run = CourseRunFactory.create(course=course)
    CourseRunGradeFactory.create(course_run=course_run, user=user, passed=True, grade=1)
    CourseRunCertificateFactory.create(user=user, course_run=course_run)
    manage_program_certificates.Command().handle(
        readable_id=program.readable_id, user=user.username
    )

    generated_certificates = ProgramCertificate.objects.filter(
        user=user, program=program
    )

    assert generated_certificates.count() == 1
