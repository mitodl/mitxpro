import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError

from cms.models import CertificatePage
from courses.factories import (
    CourseRunFactory,
    CourseRunCertificateFactory,
    ProgramFactory,
    ProgramCertificateFactory,
)
from cms.factories import CertificatePageFactory, CoursePageFactory


@pytest.mark.django_db
def test_update_certificate_for_course_run():
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

    out = StringIO()
    call_command(
        "update_certificate_revision_to_latest",
        "--course_run_id",
        str(course_run.id),
        stdout=out,
    )

    certificate.refresh_from_db()
    assert certificate.certificate_page_revision == new_page_revision
    assert f"Successfully updated 1 course run {course_run.id} certificate(s) to latest revision." in out.getvalue()


@pytest.mark.django_db
def test_update_certificate_for_program():
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

    # Run the management command
    out = StringIO()
    call_command(
        "update_certificate_revision_to_latest",
        "--program_id",
        str(program.id),
        stdout=out,
    )

    # Assert it updated to the latest revision
    certificate.refresh_from_db()
    assert certificate.certificate_page_revision == new_cert_page_revision
    assert f"Successfully updated 1 program {program.id} certificate(s) to latest revision." in out.getvalue()


@pytest.mark.django_db
def test_course_run_not_found_raises():
    with pytest.raises(CommandError, match="CourseRun with id 9999 does not exist"):
        call_command("update_certificate_revision_to_latest", "--course_run_id", "9999")


@pytest.mark.django_db
def test_program_not_found_raises():
    with pytest.raises(CommandError, match="Program with id 9999 does not exist"):
        call_command("update_certificate_revision_to_latest", "--program_id", "9999")


@pytest.mark.django_db
def test_no_certificates_found_logs_warning_for_course_run():
    course_run = CourseRunFactory()
    out = StringIO()
    call_command(
        "update_certificate_revision_to_latest",
        "--course_run_id",
        str(course_run.id),
        stdout=out,
    )
    assert "No certificates found for course run" in out.getvalue()


@pytest.mark.django_db
def test_no_certificates_found_logs_warning_for_program():
    program = ProgramFactory()
    out = StringIO()
    call_command(
        "update_certificate_revision_to_latest",
        "--program_id",
        str(program.id),
        stdout=out,
    )
    assert "No certificates found for program" in out.getvalue()
