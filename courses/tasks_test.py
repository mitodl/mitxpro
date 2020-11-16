"""Course tasks tests"""
from mitol.digitalcredentials.factories import DigitalCredentialRequestFactory

from courses.factories import ProgramCertificateFactory
from courses.tasks import notify_digital_credential_request


def test_notify_digital_credential_request(mocker, user):
    """Test notify_digital_credential_request task"""
    mock_send_digital_credential_request_notification = mocker.patch(
        "courses.credentials.send_digital_credential_request_notification"
    )
    request = DigitalCredentialRequestFactory.create(
        learner=user, credentialed_object=ProgramCertificateFactory.create(user=user)
    )
    notify_digital_credential_request.delay(request.id)

    mock_send_digital_credential_request_notification.assert_called_once_with(request)
