"""Opt-in django-aqueduct **local-dev** settings shim for mitxpro.

Identical to ``mitxpro.settings_aqueduct`` but constructs
``DevAqueductSettings``, which layers a Vault (KV v1, mount ``secret-xpro``)
source over the environment when ``VAULT_ADDR`` is set. With ``VAULT_ADDR``
unset it behaves exactly like the production shim (plain env/.env dev), so
this module is safe to select without a running Vault.

This module is **not** used by default. Select it explicitly with::

    DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct_dev

See ``docs/aqueduct.md`` and ``django_aqueduct.sources.dev`` for the
``VAULT_*`` environment variables that configure the Vault source.

Sentry is initialized here, before the settings model is constructed, in the
same relative order as ``mitxpro/settings.py`` so configuration errors raised
while building the model are still reported.
"""

import os

from django_aqueduct import configure_django_settings

from mitxpro.aqueduct_settings import VERSION, DevAqueductSettings
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

configure_django_settings(DevAqueductSettings)
