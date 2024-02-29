"""Tests for Program Certificates management command"""

from itertools import product

import pytest
from django.core.management.base import CommandError

from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    CourseRunGradeFactory,
    ProgramFactory,
)
from courses.management.commands import manage_program_certificates
from courses.models import ProgramCertificate
from users.factories import UserFactory

pytestmark = [pytest.mark.django_db]


def test_program_certificate_management_no_argument():
    """Test that command throws error when no arguments are provided"""
    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle()
    assert str(command_error.value) == "Please provide a valid program readable_id."


def test_program_certificate_management_no_user_argument():
    """Test that command generates error when user is not passed"""
    program = ProgramFactory.create()
    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle(program=program.readable_id)
    assert (
        str(command_error.value)
        == f"Could not find course enrollment(s) with provided program readable_id={program.readable_id}"
    )


def test_program_certificate_management_no_program_argument(user):
    """Test that command generates error when the program is not passed"""
    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle(user=user)
    assert str(command_error.value) == "Please provide a valid program readable_id."


def test_program_certificate_creation_multiple_users():
    """
    Test that program certificate management command creates program certificates
    when no user and a valid program is supplied
    """

    def create_course_certificates(args):
        run, user = args
        (CourseRunEnrollmentFactory.create(user=user, run=run),)
        (CourseRunGradeFactory.create(course_run=run, user=user, passed=True, grade=1),)
        (CourseRunCertificateFactory.create(course_run=run, user=user),)

    program = ProgramFactory.create(readable_id="test")
    users = UserFactory.create_batch(size=3)
    courses = CourseFactory.create_batch(size=2, program=program)
    course_runs = [CourseRunFactory.create(course=course) for course in courses]

    courses_users = product(course_runs, users)
    list(map(create_course_certificates, courses_users))

    manage_program_certificates.Command().handle(program="test")
    generated_certificates = ProgramCertificate.objects.filter(program=program)

    assert generated_certificates.count() == len(users)


def test_program_not_present():
    """
    Test that program certificate management command throws proper error when
    the provided program is not found
    """
    with pytest.raises(CommandError) as command_error:
        manage_program_certificates.Command().handle(program="no-program")
    assert (
        str(command_error.value)
        == "Could not find any program with provided readable_id=no-program"
    )


def test_program_certificate_creation_single_user(user):
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
    Test that create operation for program certificate management command doesn't create a certificate for incomplete courses
    """

    def create_course_grades(run):
        CourseRunEnrollmentFactory.create(user=user, run=run)
        CourseRunGradeFactory.create(course_run=run, user=user, passed=True, grade=1)

    program = ProgramFactory.create()
    courses = CourseFactory.create_batch(size=2, program=program)
    course_runs = [CourseRunFactory.create(course=course) for course in courses]

    list(map(create_course_grades, course_runs))
    # Generating certificate only for a single course
    CourseRunCertificateFactory.create(user=user, course_run=course_runs[0])
    manage_program_certificates.Command().handle(
        program=program.readable_id, user=user.username
    )

    generated_certificates = ProgramCertificate.objects.filter(
        user=user, program=program
    )

    assert generated_certificates.count() == 0
