"""Digital courseware credentials"""

import logging
from urllib.parse import urljoin

from django.conf import settings
from mitol.common.utils import now_in_utc
from mitol.digitalcredentials.models import LearnerDID

from courses.models import CourseRunCertificate, ProgramCertificate

log = logging.getLogger(__name__)


def build_program_credential(certificate: ProgramCertificate) -> dict:
    """Build a credential object for a ProgramCertificate"""
    start_date, end_date = certificate.start_end_dates

    if not start_date or not end_date:
        raise Exception("Program has no start or end date")  # noqa: EM101, TRY002

    if not certificate.program.page:
        raise Exception("Program has no CMS program page")  # noqa: EM101, TRY002

    if not certificate.program.page.certificate_page:
        raise Exception("Program has no CMS program certificate page")  # noqa: EM101, TRY002

    if not certificate.program.page.certificate_page.CEUs:
        raise Exception("Program has no CEUs defined")  # noqa: EM101, TRY002

    return {
        "type": ["EducationalOccupationalCredential", "ProgramCompletionCredential"],
        "name": f"{certificate.program.title} Completion",
        "description": certificate.program.page.description,
        "awardedOnCompletionOf": {
            "identifier": certificate.program.text_id,
            "type": "EducationalOccupationalProgram",
            "name": certificate.program.title,
            "description": certificate.program.page.description,
            "numberOfCredits": {
                "value": certificate.program.page.certificate_page.normalized_ceus
            },
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    }


def build_course_run_credential(certificate: CourseRunCertificate) -> dict:
    """Build a credential object for a CourseRunCertificate"""
    course = certificate.course_run.course
    start_date, end_date = certificate.start_end_dates

    if not start_date or not end_date:
        raise Exception("CourseRun has no start or end date")  # noqa: EM101, TRY002

    if not course.page:
        raise Exception("Course has no CMS course page")  # noqa: EM101, TRY002

    if not course.page.certificate_page:
        raise Exception("Course has no CMS course certificate page")  # noqa: EM101, TRY002

    if not course.page.certificate_page.CEUs:
        raise Exception("Course has no CEUs defined")  # noqa: EM101, TRY002

    return {
        "type": ["EducationalOccupationalCredential", "CourseCompletionCredential"],
        "name": f"{course.title} Completion",
        "description": course.page.description,
        "awardedOnCompletionOf": {
            "type": ["Course", "Event"],
            "courseCode": course.readable_id,
            "name": course.title,
            "description": course.page.description,
            "numberOfCredits": {"value": course.page.certificate_page.normalized_ceus},
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    }


def build_digital_credential(
    certificate: ProgramCertificate | CourseRunCertificate,
    learner_did: LearnerDID,
) -> dict:
    """Function for building certificate digital credentials"""
    if isinstance(certificate, ProgramCertificate):
        has_credential = build_program_credential(certificate)
    elif isinstance(certificate, CourseRunCertificate):
        has_credential = build_course_run_credential(certificate)
    else:
        raise Exception(  # noqa: TRY002, TRY004
            f"Unexpected courseware object type for digital credentials: {type(certificate)}"  # noqa: EM102
        )

    return {
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
            "issuanceDate": now_in_utc().isoformat(),
            "credentialSubject": {
                "type": "schema:Person",
                "id": learner_did.did,
                "name": learner_did.learner.name,
                "hasCredential": has_credential,
            },
        },
        "options": {
            "verificationMethod": settings.DIGITAL_CREDENTIALS_VERIFICATION_METHOD
        },
    }
