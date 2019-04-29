"""API tests"""
from email.utils import formataddr
import pytest

from mail.api import (
    get_base_context,
    context_for_user,
    safe_format_recipients,
    render_email_templates,
    send_messages,
    messages_for_recipients,
    build_messages,
)
from users.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("email_settings")]
lazy = pytest.lazy_fixture


@pytest.fixture
def email_settings(settings):
    """Default settings for email tests"""
    settings.MAILGUN_RECIPIENT_OVERRIDE = None


def test_safe_format_recipients():
    """Test that we get a list of emailable recipients"""
    user = UserFactory.create()
    user_no_email = UserFactory.create(email="")
    user_no_name = UserFactory.create(name="")
    assert safe_format_recipients([user, user_no_email, user_no_name]) == [
        (formataddr((user.name, user.email)), user),
        (formataddr((None, user_no_name.email)), user_no_name),
    ]


def test_safe_format_recipients_override(user, settings):
    """Test that the recipient override works"""
    settings.MAILGUN_RECIPIENT_OVERRIDE = "admin@localhost"
    assert safe_format_recipients([user]) == [("admin@localhost", user)]


@pytest.mark.parametrize("test_user", [None, lazy("user")])
@pytest.mark.parametrize("extra_context", [None, {}, {"other": "value"}])
def test_context_for_user(settings, test_user, extra_context):
    """Tests that context_for_user returns the expected values"""
    user_ctx = {"user": test_user} if test_user else {}

    assert context_for_user(user=test_user, extra_context=extra_context) == {
        "base_url": settings.SITE_BASE_URL,
        "site_name": settings.SITE_NAME,
        **(extra_context or {}),
        **user_ctx,
    }


def test_render_email_templates(user):
    """Test render_email_templates"""
    user.name = "Jane Smith"
    context = context_for_user(user=user, extra_context={"url": "http://example.com"})
    subject, text_body, html_body = render_email_templates("sample", context)
    assert subject == "Welcome Jane Smith"
    assert text_body == "html link (http://example.com)"
    assert html_body == (
        '<style type="text/css">\n'
        "a {\n"
        "  color: red;\n"
        "}\n"
        "</style>\n"
        '<a href="http://example.com">html link</a>\n'
    )


def test_messages_for_recipients():
    """Tests that messages_for_recipients works as expected"""

    users = UserFactory.create_batch(5)

    messages = list(
        messages_for_recipients(
            [
                (
                    recipient,
                    context_for_user(
                        user=user, extra_context={"url": "https://example.com"}
                    ),
                )
                for recipient, user in safe_format_recipients(users)
            ],
            "sample",
        )
    )

    assert len(messages) == len(users)

    for user, msg in zip(users, messages):
        assert user.email in str(msg.to[0])
        assert msg.subject == "Welcome {}".format(user.name)


def test_build_messages(mocker):
    """
    Tests that build_messages creates message objects for a set of recipients with the correct context
    """
    mock_msg = mocker.Mock()
    patched_msg_class = mocker.patch("mail.api.AnymailMessage", return_value=mock_msg)
    patched_render = mocker.patch(
        "mail.api.render_email_templates",
        return_value=("subject", "text body", "<p>html body</p>"),
    )

    template_name = "sample"
    recipients = ["a@b.com", "c@d.com"]
    extra_context = {"extra": "context"}
    messages = list(build_messages(template_name, recipients, extra_context))
    assert patched_render.call_args[0] == (
        template_name,
        {**extra_context, **get_base_context()},
    )
    assert patched_msg_class.call_count == len(recipients)
    assert messages == [mock_msg] * len(recipients)


def test_send_message(mailoutbox):
    """Tests that send_messages works as expected"""
    users = UserFactory.create_batch(5)

    messages = list(
        messages_for_recipients(
            [
                (
                    recipient,
                    context_for_user(
                        user=user, extra_context={"url": "https://example.com"}
                    ),
                )
                for recipient, user in safe_format_recipients(users)
            ],
            "sample",
        )
    )

    send_messages(messages)

    for message in mailoutbox:
        assert message in messages


def test_send_message_failure(mocker):
    """Tests that send_messages logs all exceptions"""
    sendmail = mocker.patch("mail.api.AnymailMessage.send", side_effect=ConnectionError)
    patched_logger = mocker.patch("mail.api.log")
    users = UserFactory.create_batch(2)

    messages = list(
        messages_for_recipients(
            [
                (
                    recipient,
                    context_for_user(
                        user=user, extra_context={"url": "https://example.com"}
                    ),
                )
                for recipient, user in safe_format_recipients(users)
            ],
            "sample",
        )
    )

    send_messages(messages)

    assert sendmail.call_count == len(users)
    assert patched_logger.exception.call_count == len(users)
