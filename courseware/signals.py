"""Courseware signals"""
import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from courseware import api
from courseware import tasks

log = logging.getLogger()

CREATE_COURSEWARE_USER_RETRY_DELAY = 60


def _create_courseware_user(user):
    """
    Create a user in the courseware, deferring a retry via celery if it fails

    Args:
        user (users.models.User): the user that was just created
    """
    try:
        api.create_user(user)
    except Exception:  # pylint: disable=broad-except
        log.exception("Error creating courseware user records on User create")
        # try again later
        tasks.create_user_from_id.apply_async(
            (user.id,), countdown=CREATE_COURSEWARE_USER_RETRY_DELAY
        )


@receiver(
    post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="create_courseware_user"
)
def create_courseware_user(
    sender, instance, created, **kwargs
):  # pylint:disable=unused-argument
    """
    Create the user in the courseware
    """
    if created:
        transaction.on_commit(lambda: _create_courseware_user(instance))
