import datetime
import logging

from django.conf import settings
from django.db import transaction

from ecommerce.api import clear_baskets
from ecommerce.models import Basket
from mitxpro.celery import app
from mitxpro.utils import now_in_utc

log = logging.getLogger(__name__)


@app.task(acks_late=True)
def delete_expired_baskets():
    cutoff_date = now_in_utc() - datetime.timedelta(days=settings.BASKET_EXPIRY_DAYS)
    log.info("Starting the deletion of expired baskets at %s", now_in_utc())

    with transaction.atomic():
        expired_baskets = Basket.objects.filter(
            id__in=(
                Basket.objects.select_for_update(skip_locked=True).filter(
                    updated_on__lte=cutoff_date
                )
            )
        )
        expired_basket_ids = expired_baskets.values_list("id", flat=True)
        log.info("Found %d expired baskets to delete", len(expired_basket_ids))
        if expired_basket_ids:
            clear_baskets(expired_basket_ids)
            expired_baskets.delete()
