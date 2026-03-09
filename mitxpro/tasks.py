"""mitxpro tasks"""

import logging

from celery import shared_task
from oauth2_provider.models import clear_expired

log = logging.getLogger(__name__)


@shared_task(acks_late=True)
def clear_expired_tokens():
    """Clear expired OAuth2 access, refresh, and ID tokens."""
    log.info("Starting clear_expired_tokens...")
    clear_expired()
    log.info("Finished clear_expired_tokens.")
