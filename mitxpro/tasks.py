"""mitxpro tasks"""

import logging

from django.core.management import call_command

from mitxpro.celery import app

log = logging.getLogger(__name__)


@app.task(acks_late=True)
def clear_expired_tokens():
    """Clear expired OAuth2 access, refresh, and ID tokens via the cleartokens management command."""
    log.info("Starting clear_expired_tokens...")
    call_command("cleartokens")
    log.info("Finished clear_expired_tokens.")
