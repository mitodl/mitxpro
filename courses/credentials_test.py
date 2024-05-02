"""Credentials tests"""

from urllib.parse import urljoin

import pytest
from mitol.common.pytest_utils import any_instance_of
from mitol.digitalcredentials.factories import LearnerDIDFactory

from courses.credentials import (
    build_course_run_credential,
    build_digital_credential,
    build_program_credential,
)
from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunFactory,
    ProgramCertificateFactory,
    ProgramFactory,
)

pytestmark = pytest.mark.django_db


def test_build_program_credential(user):
    """Build a program run completion object"""
    certificate = ProgramCertificateFactory.create(user=user)
    course_run_certificate = CourseRunCertificateFactory.create(
        user=user, course_run__course__program=certificate.program
    )
    course_run = course_run_certificate.course_run
    program = certificate.program
    assert build_program_credential(certificate) == {
        "type": ["EducationalOccupationalCredential", "ProgramCompletionCredential"],
        "name": f"{program.title} Completion",
        "description": program.page.description,
        "awardedOnCompletionOf": {
            "identifier": program.text_id,
            "type": "EducationalOccupationalProgram",
            "name": program.title,
            "description": program.page.description,
            "numberOfCredits": {"value": program.page.certificate_page.CEUs},
            "startDate": course_run.start_date.isoformat(),
            "endDate": course_run.end_date.isoformat(),
        },
    }


@pytest.mark.parametrize(
    "kwargs, error_message",  # noqa: PT006
    [
        ({"page": None}, "Program has no CMS program page"),
        (
            {"page__certificate_page": None},
            "Program has no CMS program certificate page",
        ),
        ({"page__certificate_page__CEUs": None}, "Program has no CEUs defined"),
    ],
)
def test_build_program_credential_error(user, kwargs, error_message):
    """Verify build_program_credential errors with invalid state"""
    program = ProgramFactory.create(**kwargs)
    certificate = ProgramCertificateFactory.create(user=user, program=program)
    CourseRunCertificateFactory.create(user=user, course_run__course__program=program)
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        build_program_credential(certificate)

    assert exc_info.value.args[0] == error_message


def test_build_program_credential_no_start_end_dates_error():
    """Verify build_program_credential errors with no start or end dates"""
    certificate = ProgramCertificateFactory.create()
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        build_program_credential(certificate)

    assert exc_info.value.args[0] == "Program has no start or end date"


def test_build_course_run_credential():
    """Build a course run completion object"""
    certificate = CourseRunCertificateFactory.create()
    course_run = certificate.course_run
    start_date, end_date = certificate.start_end_dates
    course = course_run.course
    assert build_course_run_credential(certificate) == {
        "type": ["EducationalOccupationalCredential", "CourseCompletionCredential"],
        "name": f"{course.title} Completion",
        "description": course.page.description,
        "awardedOnCompletionOf": {
            "type": ["Course", "Event"],
            "courseCode": course.readable_id,
            "name": course.title,
            "description": course.page.description,
            "numberOfCredits": {"value": course.page.certificate_page.CEUs},
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    }


@pytest.mark.parametrize(
    "kwargs, error_message",  # noqa: PT006
    [
        ({"course__page": None}, "Course has no CMS course page"),
        (
            {"course__page__certificate_page": None},
            "Course has no CMS course certificate page",
        ),
        ({"course__page__certificate_page__CEUs": None}, "Course has no CEUs defined"),
        ({"start_date": None}, "CourseRun has no start or end date"),
        ({"end_date": None}, "CourseRun has no start or end date"),
    ],
)
def test_build_course_run_credential_error(kwargs, error_message):
    """Verify build_course_run_credential errors with invalid state"""
    course_run = CourseRunFactory.create(**kwargs)
    certificate = CourseRunCertificateFactory.create(course_run=course_run)

    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        build_course_run_credential(certificate)

    assert exc_info.value.args[0] == error_message


def test_build_digital_credential_course_run(settings, mocker):
    """Verify build_digital_credential works correctly for a course run"""
    mock_build_course_run_credential = mocker.patch(
        "courses.credentials.build_course_run_credential", autospec=True
    )
    course_run = CourseRunFactory.create()
    learner_did = LearnerDIDFactory.create()
    certificate = CourseRunCertificateFactory.create(
        user=learner_did.learner, course_run=course_run
    )

    assert build_digital_credential(certificate, learner_did) == {
        "credential": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1",
                "https://w3id.org/dcc/v1",
            ],
            "id": urljoin(settings.SITE_BASE_URL, certificate.link),
            "type": ["VerifiableCredential", "LearningCredential"],
            "issuer": {
                "type": "Issuer",
                "id": settings.DIGITAL_CREDENTIALS_ISSUER_ID,
                "name": settings.SITE_NAME,
                "url": settings.SITE_BASE_URL,
            },
            "issuanceDate": any_instance_of(str),
            "credentialSubject": {
                "type": "schema:Person",
                "id": learner_did.did,
                "name": learner_did.learner.name,
                "hasCredential": mock_build_course_run_credential.return_value,
            },
        },
        "options": {
            "verificationMethod": settings.DIGITAL_CREDENTIALS_VERIFICATION_METHOD
        },
    }

    mock_build_course_run_credential.assert_called_once_with(certificate)


def test_build_digital_credential_program_run(settings, mocker):
    """Verify build_digital_credential works correctly for a program run"""
    mock_build_program_credential = mocker.patch(
        "courses.credentials.build_program_credential", autospec=True
    )
    program = ProgramFactory.create()
    learner_did = LearnerDIDFactory.create()
    certificate = ProgramCertificateFactory.create(
        user=learner_did.learner, program=program
    )

    assert build_digital_credential(certificate, learner_did) == {
        "credential": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1",
                "https://w3id.org/dcc/v1",
            ],
            "id": urljoin(settings.SITE_BASE_URL, certificate.link),
            "type": ["VerifiableCredential", "LearningCredential"],
            "issuer": {
                "type": "Issuer",
                "id": settings.DIGITAL_CREDENTIALS_ISSUER_ID,
                "name": settings.SITE_NAME,
                "url": settings.SITE_BASE_URL,
            },
            "issuanceDate": any_instance_of(str),
            "credentialSubject": {
                "type": "schema:Person",
                "id": learner_did.did,
                "name": learner_did.learner.name,
                "hasCredential": mock_build_program_credential.return_value,
            },
        },
        "options": {
            "verificationMethod": settings.DIGITAL_CREDENTIALS_VERIFICATION_METHOD
        },
    }
    mock_build_program_credential.assert_called_once_with(certificate)


def test_test_build_digital_credential_invalid_certified_object(mocker):
    """Verify an exception is raised for an invalid courseware object"""
    invalid_courseware = CourseFactory.create()
    with pytest.raises(Exception):  # noqa: B017, PT011
        build_digital_credential(invalid_courseware, mocker.Mock())
