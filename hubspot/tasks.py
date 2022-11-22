"""
Hubspot tasks
"""
import logging
import re

import celery
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from b2b_ecommerce.models import B2B_INTEGRATION_PREFIX
from ecommerce.models import Order, Line
from hubspot.api import (
    send_hubspot_request,
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_b2b_deal_sync_message,
    make_line_item_sync_message,
    make_b2b_product_sync_message,
    make_b2b_contact_sync_message,
    get_sync_errors,
    hubspot_timestamp,
    parse_hubspot_id,
    exists_in_hubspot,
)
from hubspot.models import HubspotErrorCheck, HubspotLineResync
from mitxpro.celery import app
from mitxpro.utils import now_in_utc

log = logging.getLogger()

HUBSPOT_SYNC_URL = "/extensions/ecomm/v1/sync-messages"
ASSOCIATED_DEAL_RE = re.compile(r"\[hs_assoc__deal_id: (.+)\]")


@app.task
def sync_contact_with_hubspot(user_id):
    """Send a sync-message to sync a user with a hubspot contact"""
    body = make_contact_sync_message(user_id)
    response = send_hubspot_request("CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def sync_product_with_hubspot(product_id):
    """Send a sync-message to sync a product with a hubspot product"""
    body = make_product_sync_message(product_id)
    response = send_hubspot_request("PRODUCT", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def sync_b2b_contact_with_hubspot(email):
    """Send a sync-message to sync a user with a hubspot b2b contact"""
    body = make_b2b_contact_sync_message(email)
    response = send_hubspot_request("CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task(bind=True)
def sync_b2b_deal_with_hubspot(self, order_id):  # pylint: disable=unused-argument
    """Send a sync-message to sync a b2b order with a hubspot deal"""
    body = make_b2b_deal_sync_message(order_id)
    response = send_hubspot_request("DEAL", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()

    index_tasks = celery.group([sync_b2b_product_with_hubspot.si(order_id)])
    raise self.replace(celery.chain(index_tasks))


@app.task
def sync_b2b_product_with_hubspot(order_id):
    """Send a sync-message to sync a line with a hubspot line item"""
    body = make_b2b_product_sync_message(order_id)
    response = send_hubspot_request("LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task(bind=True)
def sync_deal_with_hubspot(self, order_id):
    """Send a sync-message to sync an order with a hubspot deal"""
    order = Order.objects.get(id=order_id)
    body = make_deal_sync_message(order_id)
    response = send_hubspot_request("DEAL", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()
    index_tasks = celery.group(
        [sync_line_item_with_hubspot.si(line.id) for line in order.lines.all()]
    )
    raise self.replace(celery.chain(index_tasks))


@app.task
def sync_line_item_with_hubspot(line_id):
    """Send a sync-message to sync a line with a hubspot line item"""
    body = make_line_item_sync_message(line_id)
    response = send_hubspot_request("LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def check_hubspot_api_errors():
    """Check for and log any errors that occurred since the last time this was run"""
    if not settings.HUBSPOT_API_KEY:
        return
    last_check, _ = HubspotErrorCheck.objects.get_or_create(
        defaults={"checked_on": now_in_utc()}
    )
    last_timestamp = hubspot_timestamp(last_check.checked_on)

    for error in get_sync_errors():
        error_timestamp = error.get("errorTimestamp")
        if error_timestamp > last_timestamp:
            obj_type = (error.get("objectType", "N/A"),)
            integration_id = error.get("integratorObjectId", "")
            obj_id = parse_hubspot_id(integration_id)
            error_type = error.get("type", "N/A")
            details = error.get("details", "")

            if (
                obj_id is not None
                and "LINE_ITEM" in obj_type
                and error_type == "INVALID_ASSOCIATION_PROPERTY"
                and ASSOCIATED_DEAL_RE.search(details) is not None
            ):
                if B2B_INTEGRATION_PREFIX in integration_id:
                    # ignore it, an incoming second sync attempt should clear it up
                    continue
                try:
                    line = Line.objects.get(id=obj_id)
                except ObjectDoesNotExist:
                    pass
                else:
                    HubspotLineResync.objects.get_or_create(line=line)
                    continue

            log.error(
                "Hubspot error %s for %s id %s: %s",
                error_type,
                obj_type,
                str(obj_id),
                details,
            )
        else:
            break

    retry_invalid_line_associations()
    last_check.checked_on = now_in_utc()
    last_check.save()


def retry_invalid_line_associations():
    """
    Check lines that have errored and retry them if their orders have synced
    """
    for hubspot_line_resync in HubspotLineResync.objects.all():
        if exists_in_hubspot("LINE_ITEM", hubspot_line_resync.line.id):
            hubspot_line_resync.delete()
            continue

        if exists_in_hubspot("DEAL", hubspot_line_resync.line.order_id):
            sync_line_item_with_hubspot(hubspot_line_resync.line.id)
