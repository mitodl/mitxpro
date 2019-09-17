# pylint:disable=redefined-outer-name
"""
Tests for signals
"""
import pytest
from courses.factories import (
    UserFactory,
    ProgramFactory,
    CourseFactory,
    CourseRunFactory,
    CourseRunCertificateFactory,
    ProgramCertificateFactory,
)
from courses.utils import generate_program_certificate
from courses.models import ProgramCertificate

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    """User object fixture"""
    return UserFactory.create()


@pytest.fixture()
def program():
    """User object fixture"""
    return ProgramFactory.create()


def test_generate_program_certificate_already_exist(user, program):
    """
    Test that generate_program_certificate return (None, False) and not create program certificate
    if program certificate already exist.
    """
    program_certificate = ProgramCertificateFactory.create(program=program, user=user)
    result = generate_program_certificate(user=user, program=program)
    assert result == (program_certificate, False)
    assert len(ProgramCertificate.objects.all()) == 1


def test_generate_program_certificate_failure(user, program):
    """
    Test that generate_program_certificate return (None, False) and not create program certificate
    if there is not any course_run certificate for the given course.
    """
    course = CourseFactory.create(program=program)
    CourseRunFactory.create_batch(3, course=course)

    result = generate_program_certificate(user=user, program=program)
    assert result == (None, False)
    assert len(ProgramCertificate.objects.all()) == 0


def test_generate_program_certificate_success(user, program):
    """
    Test that generate_program_certificate generate a program certificate
    """
    course = CourseFactory.create(program=program)
    course_run = CourseRunFactory.create(course=course)

    CourseRunCertificateFactory.create(user=user, course_run=course_run)

    result = generate_program_certificate(user=user, program=program)
    assert result[1] is True
    assert isinstance(result[0], ProgramCertificate)
    assert len(ProgramCertificate.objects.all()) == 1
