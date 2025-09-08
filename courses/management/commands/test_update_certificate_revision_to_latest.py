"""Tests for the update_certificate_revision_to_latest management command."""

import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from unittest.mock import patch

from cms.models import CertificatePage
from courses.factories import (
    CourseRunFactory,
    CourseRunCertificateFactory,
    ProgramFactory,
    ProgramCertificateFactory,
)
from cms.factories import CertificatePageFactory, CoursePageFactory
from courses.models import CourseRunCertificate, ProgramCertificate

pytestmark = [pytest.mark.django_db]


@pytest.mark.parametrize(
    ("update_all", "confirm_input", "should_update_all"),
    [
        (True, "y", True),  # Update all with confirmation
        (True, "yes", True),  # Update all with confirmation
        (True, "n", False),  # Update all but decline confirmation
        (False, None, True),  # Update only missing with confirmation
    ],
)
def test_update_certificate_for_course_run(
    update_all, confirm_input, should_update_all
):
    """Test updating certificate revision for a course run."""
    course_page = CoursePageFactory.create(certificate_page=None)
    course_run = CourseRunFactory(course=course_page.course)
    certificate_page = CertificatePageFactory(parent=course_page, live=True)
    certificate_page.save_revision().publish()
    cert_page_revision = certificate_page.latest_revision

    # Create a CourseRunCertificate with the initial certificate page revision
    certificate = CourseRunCertificateFactory(course_run=course_run)
    assert certificate.certificate_page_revision == cert_page_revision

    # Update the certificate page
    certificate_page.product_name = "Updated Course Certificate"
    certificate_page.save_revision().publish()
    certificate_page.refresh_from_db()
    new_page_revision = certificate_page.latest_revision
    assert certificate.certificate_page_revision != new_page_revision

    certificate_without_revision = CourseRunCertificateFactory(course_run=course_run)
    CourseRunCertificate.objects.filter(id=certificate_without_revision.id).update(
        certificate_page_revision=None
    )

    out = StringIO()
    if update_all:
        with patch("builtins.input", return_value=confirm_input):
            call_command(
                "update_certificate_revision_to_latest",
                "--course-run-id",
                str(course_run.id),
                "--all",
                stdout=out,
            )
    else:
        call_command(
            "update_certificate_revision_to_latest",
            "--course-run-id",
            str(course_run.id),
            stdout=out,
        )

    certificate.refresh_from_db()
    certificate_without_revision.refresh_from_db()
    if update_all and should_update_all:
        assert certificate.certificate_page_revision == new_page_revision
        assert (
            certificate_without_revision.certificate_page_revision == new_page_revision
        )
        assert (
            f"Updated 2 certificate(s) for course run {course_run.id} to the latest revision."
            in out.getvalue()
        )
    elif update_all and not should_update_all:
        assert certificate.certificate_page_revision != new_page_revision
        assert certificate_without_revision.certificate_page_revision is None
        assert "Operation cancelled." in out.getvalue()
    else:
        assert certificate.certificate_page_revision != new_page_revision
        assert (
            certificate_without_revision.certificate_page_revision == new_page_revision
        )
        assert (
            f"Updated 1 certificate(s) for course run {course_run.id} to the latest revision."
            in out.getvalue()
        )


@pytest.mark.parametrize(
    ("update_all", "confirm_input", "should_update_all"),
    [
        (True, "y", True),  # Update all with confirmation
        (True, "y", True),  # Update all with confirmation
        (True, "n", False),  # Update all but decline confirmation
        (False, None, True),  # Update only missing with confirmation
    ],
)
def test_update_certificate_for_program(update_all, confirm_input, should_update_all):
    """Test updating certificate revision for a program."""
    program = ProgramFactory()
    program_page = program.page
    cert_page = program_page.get_children().type(CertificatePage).first().specific
    cert_page.save_revision().publish()
    cert_page_revision = cert_page.latest_revision

    # Create a ProgramCertificate with the initial certificate page revision
    certificate = ProgramCertificateFactory(program=program)
    assert certificate.certificate_page_revision == cert_page_revision

    # Publish a new revision to simulate update
    cert_page.product_name = "Updated Program Certificate"
    cert_page.save_revision().publish()
    cert_page.refresh_from_db()
    new_cert_page_revision = cert_page.latest_revision
    assert certificate.certificate_page_revision != new_cert_page_revision

    certificate_without_revision = ProgramCertificateFactory(program=program)
    ProgramCertificate.objects.filter(id=certificate_without_revision.id).update(
        certificate_page_revision=None
    )

    # Run the management command
    out = StringIO()

    if update_all:
        with patch("builtins.input", return_value=confirm_input):
            call_command(
                "update_certificate_revision_to_latest",
                "--program-id",
                str(program.id),
                "--all",
                stdout=out,
            )
    else:
        call_command(
            "update_certificate_revision_to_latest",
            "--program-id",
            str(program.id),
            stdout=out,
        )

    # Assert it updated to the latest revision
    certificate.refresh_from_db()
    certificate_without_revision.refresh_from_db()
    if update_all and should_update_all:
        assert certificate.certificate_page_revision == new_cert_page_revision
        assert (
            certificate_without_revision.certificate_page_revision
            == new_cert_page_revision
        )
        assert (
            f"Updated 2 certificate(s) for program {program.id} to the latest revision."
            in out.getvalue()
        )
    elif update_all and not should_update_all:
        assert certificate.certificate_page_revision != new_cert_page_revision
        assert certificate_without_revision.certificate_page_revision is None
        assert "Operation cancelled." in out.getvalue()
    else:
        assert (
            certificate_without_revision.certificate_page_revision
            == new_cert_page_revision
        )
        assert certificate.certificate_page_revision != new_cert_page_revision
        assert (
            f"Updated 1 certificate(s) for program {program.id} to the latest revision."
            in out.getvalue()
        )


@pytest.mark.parametrize(
    "arg_name,arg_value,expected_error",
    [
        ("--course-run-id", "9999", "CourseRun with id 9999 does not exist"),
        ("--program-id", "9999", "Program with id 9999 does not exist"),
    ],
)
def test_missing_entities_raise_command_error(arg_name, arg_value, expected_error):
    """Test that missing entities raise a CommandError."""
    with pytest.raises(CommandError, match=expected_error):
        call_command("update_certificate_revision_to_latest", arg_name, arg_value)


@pytest.mark.parametrize(
    "arg_name,factory,warning_msg",
    [
        ("--course-run-id", CourseRunFactory, "No certificates found for course run"),
        ("--program-id", ProgramFactory, "No certificates found for program"),
    ],
)
def test_no_certificates_found_logs_warning(arg_name, factory, warning_msg):
    """Test that no certificates found logs a warning."""
    instance = factory()
    out = StringIO()
    call_command(
        "update_certificate_revision_to_latest",
        arg_name,
        str(instance.id),
        stdout=out,
    )
    assert warning_msg in out.getvalue()
