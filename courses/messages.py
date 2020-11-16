"""Course email messages"""
from types import SimpleNamespace

from mitol.mail.messages import TemplatedMessage


class DigitalCredentialAvailableMessage(TemplatedMessage):
    """Email message for digital credentials becoming available"""

    name = "Digital Credential Available"
    template_name = "mail/digital_credential_available"

    @staticmethod
    def get_debug_template_context() -> dict:
        """Returns the extra context for the email debugger"""
        return {
            "user": SimpleNamespace(name="Sally Ride"),
            "courseware_title": "Introduction to Quantum Computing",
            "deep_link_url": "http://example.com/",
        }
