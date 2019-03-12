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

from anymail.message import AnymailMessage
from bs4 import BeautifulSoup
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string

log = logging.getLogger()


def safe_format_recipients(recipients):
    """
    Returns a "safe" list of formatted recipients.
    This means if MAILGUN_RECIPIENT_OVERRIDE is set, we only use that.

    Args:
        recipients (iterable of User): recipient users

    Returns:
        list of (str, User): list of recipient emails to send to
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


def context_for_user(*, user=None, extra_context=None):
    """
    Returns an email context for the given user

    Args:
        user (User): user this email is being sent to
        extra_context (dict): additional per-user context

    Returns:
        dict: the context for this user
    """

    context = {"base_url": settings.SITE_BASE_URL}

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
    Creates the messages to the recipients using the templates

    Args:
        recipients_and_contexts (list of (str, dict)): list of users and their contexts as a dict
        template_name (str): name of the template, this should match a directory in mail/templates

    Yields:
        EmailMultiAlternatives: email message with rendered content
    """
    with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
        for recipient, context in recipients_and_contexts:
            subject, text_body, html_body = render_email_templates(
                template_name, context
            )
            msg = AnymailMessage(
                subject=subject,
                body=text_body,
                to=[recipient],
                from_email=settings.MAILGUN_FROM_EMAIL,
                connection=connection,
            )
            msg.attach_alternative(html_body, "text/html")
            yield msg


def send_messages(messages):
    """
    Sends the messages and logs any exceptions

    Args:
        messages (list of EmailMultiAlternatives): list of messages to send
    """
    for msg in messages:
        try:
            msg.send()
        except:  # pylint: disable=bare-except
            log.exception("Error sending email '%s' to %s", msg.subject, msg.to)
