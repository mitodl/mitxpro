""" Task helper functions for ecommerce """
from django.conf import settings

from hubspot import tasks


def sync_hubspot_user(user):
    """
    Trigger celery task to sync a User to Hubspot

    Args:
        user (User): The user to sync
    """
    if settings.HUBSPOT_API_KEY:
        tasks.sync_contact_with_hubspot.delay(user.id)


def sync_hubspot_b2b_deal(order):
    """
    Trigger celery task to sync a B2B order to Hubspot if it has lines

    Args:
        order (Order): The B2B order to sync
    """
    if settings.HUBSPOT_API_KEY and order:
        tasks.sync_b2b_deal_with_hubspot.apply_async(
            countdown=120, kwargs={"order_id": order.id}
        )


def sync_hubspot_b2b_contact(email):
    """
    Trigger celery task to sync a B2B contact to Hubspot

    Args:
        order (Order): The B2B order to sync
    """
    if settings.HUBSPOT_API_KEY and email:
        tasks.sync_b2b_contact_with_hubspot.delay(email)


def sync_hubspot_deal(order):
    """
    Trigger celery task to sync an order to Hubspot if it has lines

    Args:
        order (Order): The order to sync
    """
    if settings.HUBSPOT_API_KEY and order.lines.first() is not None:
        tasks.sync_deal_with_hubspot.delay(order.id)


def sync_hubspot_line(line):
    """
    Trigger celery task to sync a Line to Hubspot

    Args:
        line (Line): The line to sync
    """
    if settings.HUBSPOT_API_KEY:
        tasks.sync_line_item_with_hubspot.delay(line.id)


def sync_hubspot_product(product):
    """
    Trigger celery task to sync a Line to Hubspot

    Args:
        line (Line): The line to sync
    """
    if settings.HUBSPOT_API_KEY:
        tasks.sync_product_with_hubspot.delay(product.id)
