"""Course messages tests"""
from mitol.mail.api import get_message_sender

from courses.messages import DigitalCredentialAvailableMessage


def test_digital_credential_available_message(settings, user):
    """Test DigitalCredentialAvailableMessage rendering"""
    context = {
        **DigitalCredentialAvailableMessage.get_debug_template_context(),
        "user": user,
    }

    with get_message_sender(DigitalCredentialAvailableMessage) as sender:
        message = sender.build_message(user, context)

    assert message.subject == f"{settings.SITE_NAME} Digital Credentials Available"
    assert (
        f"Digital credentials are available for you for {context['courseware_title']}."
        in message.body
    )
