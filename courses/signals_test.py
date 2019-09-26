"""
Tests for signals
"""
from unittest.mock import patch
import pytest
from courses.factories import (
    CourseRunFactory,
    CourseRunCertificateFactory,
    UserFactory,
    CourseFactory,
)


pytestmark = pytest.mark.django_db


# pylint: disable=unused-argument
@patch("courses.signals.transaction.on_commit", side_effect=lambda callback: callback())
@patch("courses.signals.generate_program_certificate", autospec=True)
def test_create_course_certificate(generate_program_cert_mock, mock_on_commit):
    """
    Test that generate_program_certificate is called when a course
    certificate is created
    """
    user = UserFactory.create()
    course_run = CourseRunFactory.create()
    cert = CourseRunCertificateFactory.create(user=user, course_run=course_run)
    generate_program_cert_mock.assert_called_once_with(
        user, cert.course_run.course.program
    )
    cert.save()
    generate_program_cert_mock.assert_called_once_with(
        user, cert.course_run.course.program
    )


# pylint: disable=unused-argument
@patch("courses.signals.transaction.on_commit", side_effect=lambda callback: callback())
@patch("courses.signals.generate_program_certificate", autospec=True)
def test_generate_program_certificate_not_called(
    generate_program_cert_mock, mock_on_commit
):
    """
    Test that generate_program_certificate is not called when a course
    is not associated with program.
    """
    user = UserFactory.create()
    course = CourseFactory.create(program=None)
    course_run = CourseRunFactory.create(course=course)
    cert = CourseRunCertificateFactory.create(user=user, course_run=course_run)
    cert.save()
    generate_program_cert_mock.assert_not_called()
