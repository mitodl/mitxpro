"""API tests"""
from email.utils import formataddr
import pytest

from mail.api import (
    context_for_user,
    safe_format_recipients,
    render_email_templates,
    send_messages,
    messages_for_recipients,
    build_messages,
    build_user_specific_messages,
    build_message,
    UserMessageProps,
    EmailMetadata,
)
from mitxpro.test_utils import any_instance_of
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
    patched_build_message = mocker.patch("mail.api.build_message")
    patched_base_context = mocker.patch(
        "mail.api.get_base_context", return_value={"base": "context"}
    )
    patched_get_connection = mocker.patch("mail.api.mail.get_connection")
    template_name = "sample"
    recipients = ["a@b.com", "c@d.com"]
    extra_context = {"extra": "context"}
    metadata = EmailMetadata(tags=None, user_variables={"k1": "v1"})

    messages = list(
        build_messages(template_name, recipients, extra_context, metadata=metadata)
    )
    assert patched_build_message.call_count == len(recipients)
    assert len(messages) == len(recipients)
    patched_get_connection.assert_called_once()
    patched_base_context.assert_called_once()
    for recipient in recipients:
        patched_build_message.assert_any_call(
            connection=any_instance_of(mocker.Mock),
            template_name=template_name,
            recipient=recipient,
            context={"base": "context", "extra": "context"},
            metadata=metadata,
        )


def test_build_user_specific_messages(mocker):
    """
    Tests that build_user_specific_messages loops through an iterable of user message properties
    and builds a message object from each one
    """
    patched_build_message = mocker.patch("mail.api.build_message")
    mocker.patch("mail.api.get_base_context", return_value={"base": "context"})
    mocker.patch("mail.api.mail.get_connection")
    template_name = "sample"
    user_message_props_iter = [
        UserMessageProps(
            "a@b.com",
            {"first": "context"},
            metadata=EmailMetadata(tags=["tag1"], user_variables=None),
        ),
        UserMessageProps("c@d.com", {"second": "context"}),
        UserMessageProps("e@f.com"),
    ]

    messages = list(
        build_user_specific_messages(template_name, user_message_props_iter)
    )
    assert len(messages) == len(user_message_props_iter)
    for user_message_props in user_message_props_iter:
        patched_build_message.assert_any_call(
            connection=any_instance_of(mocker.Mock),
            template_name=template_name,
            recipient=user_message_props.recipient,
            context={"base": "context", **user_message_props.context},
            metadata=user_message_props.metadata,
        )


def test_build_message(mocker, settings):
    """
    Tests that build_message correctly builds a message object using the Anymail APIs
    """
    settings.MAILGUN_FROM_EMAIL = "from-email@example.com"
    settings.MITXPRO_REPLY_TO_ADDRESS = "reply-email@example.com"
    subject = "subject"
    text_body = "body"
    html_body = "<p>body</p>"
    recipient_email = "recipient@example.com"
    template_name = "my_template"
    context = {"context_key": "context_value"}
    metadata = EmailMetadata(tags=["my-tag"], user_variables={"k1": "v1", "k2": "v2"})
    patched_render = mocker.patch(
        "mail.api.render_email_templates", return_value=(subject, text_body, html_body)
    )
    patched_anymail_message = mocker.patch("mail.api.AnymailMessage")
    mock_connection = mocker.Mock()

    msg = build_message(
        mock_connection, template_name, recipient_email, context, metadata=metadata
    )
    patched_render.assert_called_once_with(template_name, context)
    patched_anymail_message.assert_called_once_with(
        subject=subject,
        body=text_body,
        to=[recipient_email],
        from_email=settings.MAILGUN_FROM_EMAIL,
        connection=mock_connection,
        headers={"Reply-To": settings.MITXPRO_REPLY_TO_ADDRESS},
    )
    msg.attach_alternative.assert_called_once_with(html_body, "text/html")
    assert msg.esp_extra == {"o:tag": ["my-tag"], "v:k1": "v1", "v:k2": "v2"}


def test_build_message_optional_params(mocker):
    """Tests that build_message correctly handles optional/None values for certain arguments"""
    template_name = "my_template"
    patched_render = mocker.patch(
        "mail.api.render_email_templates",
        return_value=("subject", "body", "<p>body</p>"),
    )
    mocker.patch("mail.api.AnymailMessage")

    msg = build_message(
        connection=mocker.Mock(),
        template_name=template_name,
        recipient="recipient@example.com",
        context=None,
        metadata=None,
    )
    patched_render.assert_called_once_with(template_name, {})
    # The "esp_extra" property should not have been assigned any value since metadata=None.
    # Since AnymailMessage is patched, that means this property should just be a Mock object.
    assert isinstance(msg.esp_extra, mocker.Mock)


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
