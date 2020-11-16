"""Digital courseware credentials"""
import logging
from typing import Dict, Union
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import reverse
from mitol.common.utils import now_in_utc
from mitol.digitalcredentials.models import DigitalCredentialRequest, LearnerDID
from mitol.mail.api import get_message_sender

from courses.messages import DigitalCredentialAvailableMessage
from courses.models import CourseRunCertificate, ProgramCertificate
from courses.tasks import notify_digital_credential_request


log = logging.getLogger(__name__)


def build_program_credential(certificate: ProgramCertificate) -> Dict:
    """Build a credential object for a ProgramCertificate"""
    start_date, end_date = certificate.start_end_dates

    if not start_date or not end_date:
        raise Exception("Program has no start or end date")

    if not certificate.program.page:
        raise Exception("Program has no CMS program page")

    if not certificate.program.page.certificate_page:
        raise Exception("Program has no CMS program certificate page")

    if not certificate.program.page.certificate_page.CEUs:
        raise Exception("Program has no CEUs defined")

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
                "value": certificate.program.page.certificate_page.CEUs
            },
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    }


def build_course_run_credential(certificate: CourseRunCertificate) -> Dict:
    """Build a credential object for a CourseRunCertificate"""
    course = certificate.course_run.course
    start_date, end_date = certificate.start_end_dates

    if not start_date or not end_date:
        raise Exception("CourseRun has no start or end date")

    if not course.page:
        raise Exception("Course has no CMS course page")

    if not course.page.certificate_page:
        raise Exception("Course has no CMS course certificate page")

    if not course.page.certificate_page.CEUs:
        raise Exception("Course has no CEUs defined")

    return {
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


def build_digital_credential(
    certificate: Union[ProgramCertificate, CourseRunCertificate],
    learner_did: LearnerDID,
) -> Dict:
    """Function for building certificate digital credentials"""
    if isinstance(certificate, ProgramCertificate):
        has_credential = build_program_credential(certificate)
    elif isinstance(certificate, CourseRunCertificate):
        has_credential = build_course_run_credential(certificate)
    else:
        raise Exception(
            f"Unexpected courseware object type for digital credentials: {type(certificate)}"
        )

    return {
        "credential": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3c-ccg.github.io/lds-jws2020/contexts/lds-jws2020-v1.json",
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


def create_and_notify_digital_credential_request(
    certificate: Union[CourseRunCertificate, ProgramCertificate]
):
    """Create a digital credential request and notify the learner"""
    if not settings.FEATURES.get("DIGITAL_CREDENTIALS", False):
        log.debug("Feature FEATURE_DIGITAL_CREDENTIALS is disabled")
        return

    digital_credential_request, created = DigitalCredentialRequest.objects.get_or_create(
        credentialed_object_id=certificate.id,
        credentialed_content_type=ContentType.objects.get_for_model(certificate),
        learner=certificate.user,
    )

    if created:
        transaction.on_commit(
            lambda: notify_digital_credential_request.delay(
                digital_credential_request.id
            )
        )


def create_deep_link_url(credential_request: DigitalCredentialRequest) -> str:
    """Creates and returns a deep link credential url"""
    params = {
        "auth_type": "code",
        "issuer": settings.SITE_BASE_URL,
        "vc_request_url": urljoin(
            settings.SITE_BASE_URL,
            reverse(
                "digital-credentials:credentials-request",
                kwargs={"uuid": credential_request.uuid},
            ),
        ),
        "challenge": credential_request.uuid,
    }

    return f"{settings.DIGITAL_CREDENTIALS_DEEP_LINK_URL}?{urlencode(params)}"


def send_digital_credential_request_notification(
    credential_request: DigitalCredentialRequest
):
    """Send an email notification for a digital credential request"""
    if not settings.FEATURES.get("DIGITAL_CREDENTIALS_EMAIL", False):
        log.debug("Feature FEATURE_DIGITAL_CREDENTIALS_EMAIL is disabled")
        return

    certificate = credential_request.credentialed_object

    if isinstance(certificate, ProgramCertificate):
        courseware_title = certificate.program.title
    elif isinstance(certificate, CourseRunCertificate):
        courseware_title = certificate.course_run.course.title
    else:
        log.error(
            "Unhandled credentialed_object for digital credential request: %s",
            credential_request,
        )
        return

    deep_link_url = create_deep_link_url(credential_request)

    with get_message_sender(DigitalCredentialAvailableMessage) as sender:
        sender.build_and_send_message(
            credential_request.learner,
            {"courseware_title": courseware_title, "deep_link_url": deep_link_url},
        )
