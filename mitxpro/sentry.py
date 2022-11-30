"""Sentry setup and configuration"""
from celery.exceptions import WorkerLostError
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


# these errors occur when a shutdown is happening (usually caused by a SIGTERM)
SHUTDOWN_ERRORS = (WorkerLostError, SystemExit)


def before_send(event, hint):
    """
    Filter or transform events before they're sent to Sentry

    Args:
        event (dict): event object
        hints (dict): event hints, see https://docs.sentry.io/platforms/python/#hints

    Returns:
        dict or None: returns the modified event or None to filter out the event
    """
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, SHUTDOWN_ERRORS):
            # so we don't want to report expected shutdown errors to sentry
            return None
    return event


def init_sentry(*, dsn, environment, version, log_level, heroku_app_name):
    """
    Initializes sentry

    Args:
        dsn (str): the sentry DSN key
        environment (str): the application environment
        version (str): the version of the application
        log_level (str): the sentry log level
        heroku_app_name (str or None): the name of the heroku review app
    """
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=version,
        before_send=before_send,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=log_level),
        ],
    )

    with sentry_sdk.configure_scope() as scope:
        if heroku_app_name:
            scope.set_tag("review_app_name", heroku_app_name)
