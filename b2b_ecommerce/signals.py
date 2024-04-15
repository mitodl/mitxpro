"""Signals for b2b_ecommerce models"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from b2b_ecommerce.models import B2BLine, B2BOrder


@receiver(post_save, sender=B2BOrder, dispatch_uid="b2b_order_post_save")
def create_b2b_line(
    sender,  # noqa: ARG001
    instance,
    created,
    **kwargs,  # noqa: ARG001
):
    """
    Create a B2BLine object for each B2BOrder
    """
    if created:
        B2BLine.objects.get_or_create(order=instance)
