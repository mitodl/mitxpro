"""Ecommerce Tasks"""

import logging

from ecommerce.api import clear_and_delete_baskets
from mitxpro.celery import app


log = logging.getLogger(__name__)


@app.task(bind=True, acks_late=True)
def delete_expired_baskets(self):
    """Deletes the expired baskets"""
    log.info("Task ID: %s", self.request.id)

    clear_and_delete_baskets()
