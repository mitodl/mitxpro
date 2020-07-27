"""Mail API for sheets app"""
import logging
from urllib.parse import urlencode
from collections import namedtuple

from django.conf import settings

from ecommerce.constants import BULK_ENROLLMENT_EMAIL_TAG
from mail.constants import MAILGUN_API_DOMAIN
from sheets.constants import MAILGUN_API_TIMEOUT_RETRIES
from sheets.utils import format_datetime_for_mailgun
from mitxpro.utils import has_all_keys, request_get_with_timeout_retry

log = logging.getLogger(__name__)

BulkAssignmentMessage = namedtuple(
    "BulkAssignmentMessage",
    ["bulk_assignment_id", "coupon_code", "email", "event", "timestamp"],
)


def get_bulk_assignment_messages(event=None, begin=None, end=None):
    """
    Fetches bulk assignment emails for a given event (e.g.: delivered) and date range

    Args:
        event (str or None): The email event (e.g.: "delivered", "failed"). If None, the messages
            will not be filtered by a specific event type.
        begin (datetime.datetime or None): Start of query date range
        end (datetime.datetime or None): End of query date range

    Yields:
        BulkAssignmentMessage: Mailgun event data built from Mailgun's raw JSON representation
            (https://documentation.mailgun.com/en/latest/api-events.html#event-structure)

    Raises:
        requests.exceptions.HTTPError: Raised if the response has a status code indicating an error
    """
    added_params = {}
    if event:
        added_params["event"] = event
    if begin:
        added_params["begin"] = format_datetime_for_mailgun(begin)
    if end:
        added_params["end"] = format_datetime_for_mailgun(end)
    url = "https://api:{key}@{api_domain}/v3/{domain}/events?tags={tag}".format(
        key=settings.MAILGUN_KEY,
        api_domain=MAILGUN_API_DOMAIN,
        domain=settings.MAILGUN_SENDER_DOMAIN,
        tag=BULK_ENROLLMENT_EMAIL_TAG,
    )
    if added_params:
        url = "&".join((url, urlencode(added_params)))
    resp = request_get_with_timeout_retry(url, retries=MAILGUN_API_TIMEOUT_RETRIES)
    resp_data = resp.json()
    resp_items = resp_data.get("items")
    while resp_items:
        yield from (
            BulkAssignmentMessage(
                bulk_assignment_id=int(item["user-variables"]["bulk_assignment"]),
                coupon_code=item["user-variables"]["enrollment_code"],
                email=item["recipient"],
                event=item["event"],
                timestamp=item["timestamp"],
            )
            for item in resp_items
            if "user-variables" in item
            and has_all_keys(
                item["user-variables"], ["enrollment_code", "bulk_assignment"]
            )
        )
        if "paging" in resp_data and resp_data["paging"].get("next"):
            raw_next_url = resp_data["paging"]["next"]
            # The "next" url in the paging section does not contain necessary auth. Fill it in here.
            url = raw_next_url.replace(
                "/{}/".format(MAILGUN_API_DOMAIN),
                "/api:{}@{}/".format(settings.MAILGUN_KEY, MAILGUN_API_DOMAIN),
            )
            resp = request_get_with_timeout_retry(
                url, retries=MAILGUN_API_TIMEOUT_RETRIES
            )
            resp_data = resp.json()
            resp_items = resp_data.get("items")
        else:
            resp_items = None
