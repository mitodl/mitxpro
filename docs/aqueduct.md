# django-aqueduct settings (opt-in, experimental)

mitxpro has an **opt-in, non-disruptive** [django-aqueduct](https://github.com/mitodl/django-aqueduct)
settings model alongside the classic `mitol.common.envs`-based
`mitxpro/settings.py`. It is not used anywhere by default.

## What this is

- `mitxpro/aqueduct_settings.py` — a typed [pydantic](https://docs.pydantic.dev/)
  `AqueductSettings(BaseSettings)` model mirroring `mitxpro/settings.py`,
  built with django-aqueduct **codegen v2**. The bulk of the field
  declarations live in machine-owned `# >>> aqueduct:generated:*` regions
  produced by static AST discovery; the hand-written refinements
  (validators, derived settings, secret/required overrides) live in the
  `# >>> aqueduct:preserved:*` region and anywhere outside a generated
  region. Both survive regeneration.
- `mitxpro/settings_aqueduct.py` — a thin production shim that initializes
  Sentry (in the same relative order as `mitxpro/settings.py`) and then
  calls `configure_django_settings(AqueductSettings)`.
- `mitxpro/settings_aqueduct_dev.py` — the local-dev shim, identical but for
  `DevAqueductSettings`, which layers a Vault (KV v1) source over the
  environment (see below).

## Regeneration workflow (codegen v2)

Generation is configured once in `[tool.aqueduct]` in `pyproject.toml`
(source modules, output path, parity model/legacy, `parity_ignore`), so the
commands take no flags:

```
# Regenerate — merges into the aqueduct:generated regions, preserving
# everything hand-written.
python manage.py generate_aqueduct_settings

# CI drift gate — fails if the on-disk generated regions differ from a
# fresh render.
python manage.py generate_aqueduct_settings --check

# Parity gate — instantiates the model and diffs it against
# mitxpro.settings, failing on unexplained drift.
python manage.py check_aqueduct_settings
```

Notes on the configuration:

- **Source modules.** Discovery reads `mitxpro.settings` plus the four mitol
  settings modules it pulls in via `import_settings_modules`
  (`djoser_settings`, `common.settings.webpack`, `digitalcredentials`,
  `olposthog`). `mitxpro.settings` is listed last so its overrides win.
- **EnvParser inspector is disabled** (`include_envparser = false`). The
  EnvParser registry keys fields by raw environment-variable name, which
  would re-introduce the `MITXPRO_*`-named-vs-Django-named dual field sets
  that v2 collapses (see below). Static discovery of the module source
  already recovers every setting under its Django-facing name.
- **`aqueduct_settings.py` is excluded from ruff** (`[tool.ruff]
extend-exclude`) so `ruff format` in pre-commit does not reformat the
  generated regions and trip `--check`.

## The alias collapse

`mitxpro/settings.py` systematically configures a Django setting from a
differently-named environment variable — `SITE_BASE_URL` from
`MITXPRO_BASE_URL`, `EMAIL_HOST` from `MITXPRO_EMAIL_HOST`, `ENVIRONMENT`
from `MITXPRO_ENVIRONMENT`, and ~25 more. The previous (v1) model carried a
**dual set of fields** — a raw `MITXPRO_*` field plus a Django-facing
placeholder — stitched together by two hand-written copy validators
(`_apply_env_name_aliases`, `_build_derived_aliases`).

v2 static discovery recovers those relationships from the env-reader call
sites and emits them as `Field(..., validation_alias=AliasChoices('MITXPRO_BASE_URL'))`
on a single `SITE_BASE_URL` field. The dual field sets and both copy
validators are gone; the file is substantially smaller as a result.

## Derivations

Boilerplate that every mitodl app re-implemented is now sourced from
`django_aqueduct.derivations`:

- `DATABASES` / `DEFAULT_DATABASE_CONFIG` → `derivations.database_config`,
  which (unlike the old hand-written validator) never applies an `sslmode`
  OPTION to a SQLite URL — SQLite's driver rejects it.
- The Redis fallback chain (`REDISCLOUD_URL` → `REDIS_URL`, feeding the
  Celery/Wagtail cache URLs) → `derivations.first_url`.
- `CACHES` Redis entries → `derivations.redis_cache`.
- `FEATURES` → the legacy `mitol.common.envs.get_features()` scan, **plus**
  `derivations.feature_flags` overlaid over any `FEATURE_*` values supplied
  by a non-env source (e.g. Vault). This also fixes the old hand-written
  scan's divergence: `get_features()` raises `ImproperlyConfigured` on a
  non-`true`/`false` value where the old scan silently dropped it.

## Dev / Vault story (KV v1, `secret-xpro`)

mitxpro's Vault mount is `secret-xpro`, which runs the **KV v1** secrets
engine. django-aqueduct's `VaultSettingsSource` now supports `kv_version=1`,
so the previously-deferred dev Vault class ships here.

`DevAqueductSettings` (in `aqueduct_settings.py`) subclasses
`AqueductSettings` and builds a Vault source from `django_aqueduct.sources.dev`'s
`vault_source_from_env`, with mitxpro defaults injected: `VAULT_MOUNT`
defaults to `secret-xpro` and `VAULT_KV_VERSION` to `1`. Everything else is
env-driven:

| Variable                     | Purpose                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `VAULT_ADDR`                 | Vault URL. **Unset → Vault disabled**; the model runs on plain env/`.env`, identical to `AqueductSettings`. |
| `VAULT_PATH`                 | KV secret path (required when `VAULT_ADDR` is set).                                                         |
| `VAULT_MOUNT`                | KV mount; defaults to `secret-xpro`.                                                                        |
| `VAULT_KV_VERSION`           | `1` or `2`; defaults to `1`.                                                                                |
| `VAULT_AUTH_METHOD`          | `token` \| `oidc` \| `kubernetes`; default `token`. `oidc` + `VAULT_ROLE` is the interactive dev path.      |
| `VAULT_TOKEN` / `VAULT_ROLE` | Auth material for the chosen method.                                                                        |

Select it with `DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct_dev`. With
`VAULT_ADDR` unset it is safe to use without a running Vault.

## How to use it

Point `DJANGO_SETTINGS_MODULE` at one of the shims instead of the default:

```
DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct       # production shim
DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct_dev   # dev + optional Vault
```

Every environment variable stays the same as today, and no application code
changes: `configure_django_settings` injects the resolved values into
Django's settings exactly as `mitxpro/settings.py` does.

## What did _not_ change

- **`mitxpro/settings.py` is untouched** as the default settings module
  everywhere mitxpro runs today (web, worker, extra_worker, management
  commands, tests, the Procfile, Kubernetes manifests). The only edit is
  adding `django_aqueduct` to `INSTALLED_APPS` so the
  `generate_aqueduct_settings` / `check_aqueduct_settings` management
  commands are available; it registers no models and changes no runtime
  behavior.
- Required-value enforcement moves from `mitol.common.envs`'s runtime
  `validate()` (invoked from `mitxpro.apps.RootConfig.ready()`) to pydantic
  validation at model construction. Seven fields the legacy module declares
  `required=True` with no usable default — `SITE_BASE_URL`/`MITXPRO_BASE_URL`,
  `SECRET_KEY`, `MAILGUN_SENDER_DOMAIN`, `MAILGUN_KEY`, `ADMIN_EMAIL`/
  `MITXPRO_ADMIN_EMAIL`, `OPENEDX_API_CLIENT_ID`, `OPENEDX_API_CLIENT_SECRET`,
  `EXTERNAL_COURSE_SYNC_API_KEY` — are modeled as required pydantic fields, so
  a missing value fails fast at settings import.

  This closes the drift hazard the previous pass documented: under the
  aqueduct shims the `mitol.common.envs` registry is never populated, so
  `envs.validate()` (still called by `RootConfig.ready()`) passes trivially.
  Required-ness now lives in the pydantic model instead, so the shims no
  longer rely on that no-op `validate()` for enforcement.

## Parity divergences (intentional)

`check_aqueduct_settings` reports parity with 17 ignored keys (see
`[tool.aqueduct] parity_ignore` for the annotated list):

- **Raw env inputs** the model carries as fields but the legacy module reads
  inline without exposing as settings (`DATABASE_URL`, `REDIS_URL`,
  `HOST_IP`, the `MITXPRO_DB_*` toggles, `REFRESH_TOKEN_EXPIRE_SECONDS`,
  `OAUTH2_PROVIDER_ALLOWED_REDIRECT_URI_SCHEMES`, `SHEETS_DATE_TIMEZONE_NAME`,
  the `HUBSPOT_*` form GUID inputs).
- **`AWS_S3_CUSTOM_DOMAIN`** — only assigned in legacy when `USE_S3` +
  `CLOUDFRONT_DIST` are set; otherwise the model's always-present `None` field
  has no legacy counterpart.
- **`DATABASES` / `DEFAULT_DATABASE_CONFIG`** — Django's settings harness adds
  `ATOMIC_REQUESTS`/`AUTOCOMMIT`/`TIME_ZONE`/`TEST` to the live dict after
  load, and the model omits the SQLite `sslmode` OPTION the legacy module
  applies unconditionally. Both are load-time/derivation artifacts, not drift.

## Fields that still need a second look

- `CRON_*_HOURS` are typed `int | str` to preserve the legacy module's
  inconsistent literal defaults (int `0` vs str `"0"`); `crontab(...)`
  accepts either.
- `LOGGING` is imported as-is from `mitol.observability.settings.logging`
  (it embeds a factory and isn't meaningfully expressible as static fields).
