"""Opt-in django-aqueduct settings shim for mitxpro.

This module is **not** used by default. ``mitxpro.settings`` (the classic
``mitol.common.envs``-based module) remains the settings module everywhere
mitxpro runs today — this file only takes effect when something explicitly
sets::

    DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct

See ``docs/aqueduct.md`` for background and rollout status.

Sentry is initialized here, before ``AqueductSettings`` is constructed, in
the same relative order as ``mitxpro/settings.py`` (which calls
``init_sentry`` immediately after resolving ``SENTRY_DSN``/
``SENTRY_LOG_LEVEL``/``ENVIRONMENT``/``HEROKU_APP_NAME``, before any other
setting is computed) so that configuration errors raised while building the
rest of the settings model are still reported to Sentry.
"""

import os

from django_aqueduct import configure_django_settings

from mitxpro.aqueduct_settings import VERSION, AqueductSettings
from mitxpro.sentry import init_sentry

ENVIRONMENT = os.environ.get("MITXPRO_ENVIRONMENT", "dev")
HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_LOG_LEVEL = os.environ.get("SENTRY_LOG_LEVEL", "ERROR")

init_sentry(
    dsn=SENTRY_DSN,
    environment=ENVIRONMENT,
    version=VERSION,
    log_level=SENTRY_LOG_LEVEL,
    heroku_app_name=HEROKU_APP_NAME,
)

configure_django_settings(AqueductSettings)
