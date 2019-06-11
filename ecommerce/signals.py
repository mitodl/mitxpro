"""Signals for ecommerce models"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from ecommerce.models import ProductVersion
from hubspot.task_helpers import sync_hubspot_product


@receiver(post_save, sender=ProductVersion, dispatch_uid="product_post_save")
def sync_product(sender, instance, created, **kwargs):  # pylint:disable=unused-argument
    """
    Sync product to hubspot
    """
    sync_hubspot_product(instance.product)
