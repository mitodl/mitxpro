"""Ecommerce Tasks"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction

from ecommerce.api import clear_and_delete_baskets
from ecommerce.models import Basket
from mitxpro.celery import app
from mitxpro.utils import now_in_utc

log = logging.getLogger(__name__)


@app.task(acks_late=True)
def delete_expired_baskets():
    """Deletes the expired baskets"""
    cutoff_date = now_in_utc() - timedelta(days=settings.BASKET_EXPIRY_DAYS)
    log.info("Starting the deletion of expired baskets at %s", now_in_utc())

    with transaction.atomic():
        expired_basket_ids = (
            Basket.objects.select_for_update(skip_locked=True)
            .filter(updated_on__lte=cutoff_date)
            .values_list("id", flat=True)
        )
        log.info("Found %d expired baskets to delete", len(expired_basket_ids))
        if expired_basket_ids:
            clear_and_delete_baskets(expired_basket_ids)
