"""Credentials tests"""
from urllib.parse import parse_qs, urljoin, urlparse

import pytest
from django.db.models.signals import post_save
from factory.django import mute_signals
from mitol.common.pytest_utils import any_instance_of
from mitol.digitalcredentials.factories import (
    DigitalCredentialRequestFactory,
    LearnerDIDFactory,
)
from mitol.digitalcredentials.models import DigitalCredentialRequest

from courses.credentials import (
    build_course_run_credential,
    build_digital_credential,
    build_program_credential,
    create_and_notify_digital_credential_request,
    create_deep_link_url,
    send_digital_credential_request_notification,
)
from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunFactory,
    ProgramCertificateFactory,
    ProgramFactory,
)
from courses.messages import DigitalCredentialAvailableMessage


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
    "kwargs, error_message",
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
    with pytest.raises(Exception) as exc_info:
        build_program_credential(certificate)

    assert exc_info.value.args[0] == error_message


def test_build_program_credential_no_start_end_dates_error():
    """Verify build_program_credential errors with no start or end dates"""
    certificate = ProgramCertificateFactory.create()
    with pytest.raises(Exception) as exc_info:
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
    "kwargs, error_message",
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

    with pytest.raises(Exception) as exc_info:
        build_course_run_credential(certificate)

    assert exc_info.value.args[0] == error_message


def test_build_digital_credential_course_run(settings, mocker):
    "Verify build_digital_credential works correctly for a course run"
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
    "Verify build_digital_credential works correctly for a program run"
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
    with pytest.raises(Exception):
        build_digital_credential(invalid_courseware, mocker.Mock())


@pytest.mark.parametrize(
    "certificate_factory", [ProgramCertificateFactory, CourseRunCertificateFactory]
)
@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("enabled", [True, False])
def test_create_and_notify_digital_credential_request(
    settings, mocker, user, certificate_factory, exists, enabled
):  # pylint: disable=too-many-arguments
    """Test create_and_notify_digital_credential_request"""
    settings.FEATURES["DIGITAL_CREDENTIALS"] = enabled
    mocker.patch(
        "courses.credentials.transaction.on_commit",
        side_effect=lambda callback: callback(),
    )
    mock_notify_digital_credential_request = mocker.patch(
        "courses.credentials.notify_digital_credential_request", autospec=True
    )

    with mute_signals(post_save):
        certificate = certificate_factory.create(user=user)
    if exists:
        DigitalCredentialRequestFactory.create(
            learner=user, credentialed_object=certificate
        )

    create_and_notify_digital_credential_request(certificate)

    if not exists and not enabled:
        assert DigitalCredentialRequest.objects.count() == 0
    elif exists:
        mock_notify_digital_credential_request.assert_not_called()
    else:
        credential_request = DigitalCredentialRequest.objects.get(learner=user)
        mock_notify_digital_credential_request.delay.assert_called_once_with(
            credential_request.id
        )


@pytest.mark.parametrize(
    "factory", [ProgramCertificateFactory, CourseRunCertificateFactory]
)
def test_create_deep_link_url(settings, factory, user):
    """Test create_deep_link_url()"""
    settings.DIGITAL_CREDENTIALS_DEEP_LINK_URL = "scheme:site"
    certificate = factory.create()
    credential_request = DigitalCredentialRequestFactory.create(
        learner=user, credentialed_object=certificate
    )

    url = create_deep_link_url(credential_request)

    scheme, _, path, _, query, _ = urlparse(url)

    assert scheme == "scheme"
    assert path == "site"
    assert parse_qs(query) == {
        "auth_type": ["code"],
        "issuer": [settings.SITE_BASE_URL],
        "vc_request_url": [
            f"http://localhost:8053/api/v1/credentials/request/{credential_request.uuid}/"
        ],
        "challenge": [str(credential_request.uuid)],
    }


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize(
    "factory, factory_kwargs",
    [
        (ProgramCertificateFactory, {"program__title": "credential title"}),
        (
            CourseRunCertificateFactory,
            {"course_run__course__title": "credential title"},
        ),
    ],
)
def test_send_digital_credential_request_notification(
    settings, user, mocker, enabled, factory, factory_kwargs
):  # pylint: disable=too-many-arguments
    """Verify send_digital_credential_request_notification sends an email for the courseware"""
    settings.FEATURES["DIGITAL_CREDENTIALS_EMAIL"] = enabled
    certificate = factory.create(**factory_kwargs)
    credential_request = DigitalCredentialRequestFactory.create(
        learner=user, credentialed_object=certificate
    )
    mock_log = mocker.patch("courses.credentials.log")
    mock_get_message_sender = mocker.patch("courses.credentials.get_message_sender")
    mock_sender = mock_get_message_sender.return_value.__enter__.return_value
    mock_create_deep_link_url = mocker.patch("courses.credentials.create_deep_link_url")

    send_digital_credential_request_notification(credential_request)

    if not enabled:
        mock_log.debug.assert_called_once_with(
            "Feature FEATURE_DIGITAL_CREDENTIALS_EMAIL is disabled"
        )
        mock_get_message_sender.assert_not_called()
        mock_sender.build_and_send_message.assert_not_called()
    else:
        mock_log.debug.assert_not_called()
        mock_get_message_sender.assert_called_once_with(
            DigitalCredentialAvailableMessage
        )
        mock_create_deep_link_url.assert_called_once_with(credential_request)
        mock_sender.build_and_send_message.assert_called_once_with(
            credential_request.learner,
            {
                "courseware_title": "credential title",
                "deep_link_url": mock_create_deep_link_url.return_value,
            },
        )


def test_send_digital_credential_request_notification_invalid_object(
    settings, user, mocker
):  # pylint: disable=too-many-arguments
    """Verify send_digital_credential_request_notification sends an email for the courseware"""
    settings.FEATURES["DIGITAL_CREDENTIALS_EMAIL"] = True
    certificate = ProgramFactory.create()
    credential_request = DigitalCredentialRequestFactory.create(
        learner=user, credentialed_object=certificate
    )
    mock_log = mocker.patch("courses.credentials.log")
    mock_get_message_sender = mocker.patch("courses.credentials.get_message_sender")

    send_digital_credential_request_notification(credential_request)

    mock_log.error.assert_called_once_with(
        "Unhandled credentialed_object for digital credential request: %s",
        credential_request,
    )
    mock_get_message_sender.assert_not_called()
