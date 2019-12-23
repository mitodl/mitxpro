"""
Email APIs

Example usage:

# get recipients
recipients = User.objects.all()[:10]

# generator for recipient emails
messages = messages_for_recipients([
    (recipient, context_for_user(user=user, extra_context={
        # per-recipient context here
    })) for recipient, user in safe_format_recipients(recipients)
], 'sample')

# optional: anything else to `messages` beyond what `messages_for_recipients` does

# send the emails
send_messages(messages)
"""
from email.utils import formataddr
import logging
import re
from collections import namedtuple

from anymail.message import AnymailMessage
from bs4 import BeautifulSoup
from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string

from mail.exceptions import MultiEmailValidationError

log = logging.getLogger()


EmailMetadata = namedtuple("EmailMetadata", ["tags", "user_variables"])


class UserMessageProps:
    """Simple class that contains the data needed for a user-specific message"""

    def __init__(self, recipient, context=None, metadata=None):
        """
        Args:
            recipient (str): Recipient email address
            context (dict or None): Dict containing message context (defaults to empty dict)
            metadata (EmailMetadata or None): An object containing metadata to attach to the message
        """
        self.recipient = recipient
        self.context = context or {}
        self.metadata = metadata


def safe_format_recipients(recipients):
    """
    Returns a "safe" list of formatted recipients.
    This means if MAILGUN_RECIPIENT_OVERRIDE is set, we only use that.

    Args:
        recipients (iterable of User): recipient users

    Returns:
        list of User: list of users to send to
    """
    if not recipients:
        return []

    # we set this for local development so we don't actually email someone
    if settings.MAILGUN_RECIPIENT_OVERRIDE is not None:
        return [(settings.MAILGUN_RECIPIENT_OVERRIDE, recipients[0])]

    return [
        (formataddr((user.name, user.email)), user)
        for user in recipients
        if can_email_user(user)
    ]


def can_email_user(user):
    """
    Returns True if the user has an email and hasn't opted out

    Args:
        user (User): user to checklist

    Returns:
        bool: True if we can email this user
    """
    return bool(user.email)


def get_base_context():
    """Returns a dict of context variables that are needed in all emails"""
    return {"base_url": settings.SITE_BASE_URL, "site_name": settings.SITE_NAME}


def context_for_user(*, user=None, extra_context=None):
    """
    Returns an email context for the given user

    Args:
        user (User): user this email is being sent to
        extra_context (dict): additional per-user context

    Returns:
        dict: the context for this user
    """
    context = get_base_context()

    if user:
        context.update({"user": user})

    if extra_context is not None:
        context.update(extra_context)

    return context


def render_email_templates(template_name, context):
    """
    Renders the email templates for the email

    Args:
        template_name (str): name of the template, this should match a directory in mail/templates
        context (dict): context data for the email

    Returns:
        (str, str, str): tuple of the templates for subject, text_body, html_body
    """
    subject_text = render_to_string(
        "{}/subject.txt".format(template_name), context
    ).rstrip()

    context.update({"subject": subject_text})
    html_text = render_to_string("{}/body.html".format(template_name), context)

    # pynliner internally uses bs4, which we can now modify the inlined version into a plaintext version
    # this avoids parsing the body twice in bs4
    soup = BeautifulSoup(html_text, "html5lib")
    for link in soup.find_all("a"):
        link.replace_with("{} ({})".format(link.string, link.attrs["href"]))

    # clear any surviving style and title tags, so their contents don't get printed
    for style in soup.find_all(["style", "title"]):
        style.clear()  # clear contents, just removing the tag isn't enough

    fallback_text = soup.get_text().strip()
    # truncate more than 3 consecutive newlines
    fallback_text = re.sub(r"\n\s*\n", "\n\n\n", fallback_text)
    # ltrim the left side of all lines
    fallback_text = re.sub(
        r"^([ ]+)([\s\\X])", r"\2", fallback_text, flags=re.MULTILINE
    )

    return subject_text, fallback_text, html_text


def messages_for_recipients(recipients_and_contexts, template_name):
    """
    Creates message objects for a set of recipients with user-specific context in each message.

    Args:
        recipients_and_contexts (list of (str, dict)): list of users and their contexts as a dict
        template_name (str): name of the template, this should match a directory in mail/templates

    Yields:
        django.core.mail.EmailMultiAlternatives: email message with rendered content
    """
    with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
        for recipient, context in recipients_and_contexts:
            yield build_message(
                connection=connection,
                template_name=template_name,
                recipient=recipient,
                context=context,
            )


def message_for_recipient(recipient, context, template_name):
    """
    Creates message object for a recipient with user-specific context in the message.

    Args:
        recipient (User): recipient user
        context (dict): context dictionary for the email
        template_name (str): name of the template, this should match a directory in mail/templates

    Returns:
        django.core.mail.EmailMultiAlternatives: email message with rendered content
    """
    return list(messages_for_recipients([(recipient, context)], template_name))[0]


def build_messages(template_name, recipients, extra_context, metadata=None):
    """
    Creates message objects for a set of recipients with the same context in each message.

    Args:
        template_name (str): name of the template, this should match a directory in mail/templates
        recipients (iterable of str): Iterable of user email addresses
        extra_context (dict or None): A dict of context variables to pass into the template (in addition
            to the base context variables)
        metadata (EmailMetadata or None): An object containing extra data to attach to the message

    Yields:
        django.core.mail.EmailMultiAlternatives: email message with rendered content
    """
    context = {**get_base_context(), **(extra_context or {})}
    with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
        for recipient in recipients:
            yield build_message(
                connection=connection,
                template_name=template_name,
                recipient=recipient,
                context=context,
                metadata=metadata,
            )


def build_user_specific_messages(template_name, user_message_props_iter):
    """
    Creates message objects for a set of recipients with a specific context for each recipient in each message.

    Args:
        template_name (str): name of the template, this should match a directory in mail/templates
        user_message_props_iter (iterable of UserMessageProps): Iterable of objects containing user message data

    Yields:
        django.core.mail.EmailMultiAlternatives: email message with rendered content
    """
    with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
        for user_message_props in user_message_props_iter:
            yield build_message(
                connection=connection,
                template_name=template_name,
                recipient=user_message_props.recipient,
                context={**get_base_context(), **user_message_props.context},
                metadata=user_message_props.metadata,
            )


def build_message(connection, template_name, recipient, context, metadata=None):
    """
    Creates a message object

    Args:
        connection: An instance of the email backend class (return value of django.core.mail.get_connection)
        template_name (str): name of the template, this should match a directory in mail/templates
        recipient (str): Recipient email address
        context (dict or None): A dict of context variables
        metadata (EmailMetadata or None): An object containing extra data to attach to the message

    Returns:
        django.core.mail.EmailMultiAlternatives: email message with rendered content
    """
    subject, text_body, html_body = render_email_templates(template_name, context or {})
    msg = AnymailMessage(
        subject=subject,
        body=text_body,
        to=[recipient],
        from_email=settings.MAILGUN_FROM_EMAIL,
        connection=connection,
        headers={"Reply-To": settings.MITXPRO_REPLY_TO_ADDRESS},
    )
    esp_extra = {}
    if metadata:
        if metadata.tags:
            esp_extra.update({"o:tag": metadata.tags})
        if metadata.user_variables:
            esp_extra.update(
                {"v:{}".format(k): v for k, v in metadata.user_variables.items()}
            )
    if esp_extra:
        msg.esp_extra = esp_extra
    msg.attach_alternative(html_body, "text/html")
    return msg


def send_messages(messages):
    """
    Sends the messages and logs any exceptions

    Args:
        messages (list of django.core.mail.EmailMultiAlternatives): list of messages to send
    """
    for msg in messages:
        try:
            msg.send()
        except:  # pylint: disable=bare-except
            log.exception("Error sending email '%s' to %s", msg.subject, msg.to)


def send_message(message):
    """
    Convenience method for sending one message

    Args:
        message (django.core.mail.EmailMultiAlternatives): message to send
    """
    send_messages([message])


def validate_email_addresses(email_addresses):
    """
    Validates a group of email addresses. A single exception is raised with the list of all invalid
    emails if any of the email addresses fails validation.

    Args:
        email_addresses (iterable of str): An iterable of email addresses

    Raises:
        MultiEmailValidationError: Raised if any of the emails fail validation
    """
    invalid_emails = set()
    for email in email_addresses:
        try:
            validate_email(email)
        except ValidationError:
            invalid_emails.add(email)
    if invalid_emails:
        raise MultiEmailValidationError(invalid_emails)
