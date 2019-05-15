"""
Ecommerce tasks
"""
from ecommerce.hubspot_api import (
    send_hubspot_request,
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
)
from mitxpro.celery import app


HUBSPOT_SYNC_URL = "/extensions/ecomm/v1/sync-messages"


@app.task
def sync_contact_with_hubspot(user_id):
    """Send a sync-message to sync a user with a hubspot contact"""
    body = [make_contact_sync_message(user_id)]
    response = send_hubspot_request("CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def sync_product_with_hubspot(product_id):
    """Send a sync-message to sync a product with a hubspot product"""
    body = [make_product_sync_message(product_id)]
    response = send_hubspot_request("PRODUCT", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def sync_deal_with_hubspot(order_id):
    """Send a sync-message to sync an order with a hubspot deal"""
    body = [make_deal_sync_message(order_id)]
    response = send_hubspot_request("DEAL", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()


@app.task
def sync_line_item_with_hubspot(line_id):
    """Send a sync-message to sync a line with a hubspot line item"""
    body = [make_line_item_sync_message(line_id)]
    response = send_hubspot_request("LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body)
    response.raise_for_status()
