"""Signals for ecommerce models"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from ecommerce.models import ProductVersion, Line
from hubspot.task_helpers import sync_hubspot_product, sync_hubspot_line


@receiver(post_save, sender=ProductVersion, dispatch_uid="product_post_save")
def sync_product(sender, instance, created, **kwargs):  # pylint:disable=unused-argument
    """
    Sync product to hubspot
    """
    sync_hubspot_product(instance.product)


@receiver(post_save, sender=Line, dispatch_uid="line_post_save")
def sync_line(sender, instance, created, **kwargs):  # pylint:disable=unused-argument
    """
    Sync line to hubspot
    """
    sync_hubspot_line(instance)
