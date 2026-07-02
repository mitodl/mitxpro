# django-aqueduct settings (opt-in, experimental)

mitxpro has an **opt-in, non-disruptive** [django-aqueduct](https://github.com/mitodl/django-aqueduct)
settings module alongside the classic one. It is not used anywhere by
default.

## What this is

- `mitxpro/aqueduct_settings.py` — a typed [pydantic](https://docs.pydantic.dev/)
  `AqueductSettings(BaseSettings)` model that mirrors every setting in
  `mitxpro/settings.py`, generated with
  `manage.py generate_aqueduct_settings --modules mitxpro.settings --include-envparser`
  and then hand-refined with `model_validator`s for the settings that
  `mitxpro/settings.py` computes from other settings (`FEATURES`, the S3
  cross-field check, `CELERY_BEAT_SCHEDULE`, the Redis URL fallback chain,
  `SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS`, the `INSTALLED_APPS`/`MIDDLEWARE`
  dev/prod conditionals, `DATABASES`, `CACHES`, etc).
- `mitxpro/settings_aqueduct.py` — a thin shim that initializes Sentry (in
  the same relative order as `mitxpro/settings.py`) and then calls
  `configure_django_settings(AqueductSettings)` to inject the model's values
  into Django's settings.

## How to use it

Point `DJANGO_SETTINGS_MODULE` at the new module instead of the default:

```
DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct
```

Every other environment variable stays the same as today — the new module
reads the same variable names (`SECRET_KEY`, `MITXPRO_BASE_URL`,
`MAILGUN_KEY`, etc). No application code needs to change:
`django.conf.settings.FOO` access works identically because
`configure_django_settings` injects the resolved values into Django's
settings the same way `mitxpro/settings.py` does.

## What did _not_ change

- **`mitxpro/settings.py` is untouched** and remains the default settings
  module everywhere mitxpro runs today (web, worker, extra_worker,
  management commands, tests, `DJANGO_SETTINGS_MODULE` in the Procfile,
  Kubernetes manifests, etc). Nothing about the existing deployment changes
  unless `DJANGO_SETTINGS_MODULE` is explicitly repointed.
- Required-value enforcement moves from `mitol.common.envs.EnvParser`'s
  runtime `validate()` call (invoked from `mitxpro.apps.RootConfig.ready()`)
  to pydantic's own validation at `AqueductSettings()` construction time.
  Fields that were declared `required=True` with no usable default in
  `mitxpro/settings.py` (`SITE_BASE_URL`/`MITXPRO_BASE_URL`, `SECRET_KEY`,
  `MAILGUN_SENDER_DOMAIN`, `MAILGUN_KEY`, `ADMIN_EMAIL`/`MITXPRO_ADMIN_EMAIL`,
  `OPENEDX_API_CLIENT_ID`, `OPENEDX_API_CLIENT_SECRET`,
  `EXTERNAL_COURSE_SYNC_API_KEY`) are modeled as required pydantic fields
  with no default, so a missing value now fails fast at settings import
  time with a pydantic `ValidationError` instead of at Django app-registry
  `ready()` time. Note that under `mitxpro.settings_aqueduct`, the
  `mitol.common.envs` `EnvParser` registry is never populated (no
  `get_string`/`get_bool`/etc. calls run), so `envs.validate()` — still
  invoked by `mitxpro.apps.RootConfig.ready()` because `mitxpro` remains an
  installed app — passes trivially. Validation now happens through the
  pydantic model instead.

## Why there's no Vault-backed dev settings class yet

django-aqueduct ships a `VaultSettingsSource` for pulling secrets straight
from HashiCorp Vault, and (as of this writing) it supports both KV v2 and
KV v1 mounts. mitxpro's Vault mount is `secret-xpro`, which is **KV v1**.

This first pass deliberately keeps the rollout to the validate-only shim
described above and does **not** add a `DevAqueductSettings`/Vault-backed
settings class for mitxpro, even though django-aqueduct's KV v1 support
would technically allow it now. That's a natural follow-up once the
validate-only shim has seen some real-world use: a `DevAqueductSettings`
subclass could source local-dev secrets from `secret-xpro` via
`VaultSettingsSource(..., kv_version=1)` instead of `.env` files, without
touching `mitxpro/settings.py` or `mitxpro/aqueduct_settings.py`.

## Fields that need a second look

A few settings couldn't be modeled with full confidence and are worth
revisiting before this shim is used anywhere real:

- `ADMIN_EMAIL`/`MITXPRO_ADMIN_EMAIL`: `mitxpro/settings.py` declares this
  `required=True` but with a default of `""`, and `mitol`'s `validate()`
  treats an empty string as "missing" — so in practice it behaves as
  required today. The pydantic model keeps the non-required `default=""`
  for backwards compatibility (an empty value here just means "no admins"),
  rather than making it a hard-required field.
- `CRON_*_HOURS`/`CRON_*_DAYS` (used to build `crontab(...)` kwargs for
  `CELERY_BEAT_SCHEDULE`): the original code passes a mix of `int` and `str`
  literals as defaults (e.g. `CRON_COURSE_CERTIFICATES_HOURS` defaults to
  the int `0`, `CRON_EXTERNAL_COURSERUN_SYNC_HOURS` defaults to the str
  `"0"`). The model types these `int | str` to preserve the original
  (inconsistent) defaults rather than normalizing them.
- `LOGGING` is imported as-is from `mitol.observability.settings.logging`
  inside a `model_validator` (it embeds a factory function and isn't
  meaningfully expressible as static pydantic fields).
