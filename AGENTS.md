# MIT xPRO - Agent Instructions

Django 4.2 + Wagtail 5.2 + React 16 monolith for MIT xPRO professional education. Integrates with Open edX, HubSpot, Google Sheets, and CyberSource/Stripe payments.

## Architecture

- **Backend**: Django + DRF REST API + Wagtail CMS + Celery task queue + PostgreSQL + Redis
- **Frontend**: React 16 + Redux (redux-query) + Flow types + SCSS, bundled with Webpack 5
- **Entry points**: `static/js/entry/{root,header,style,django}.js`
- **CMS API**: Wagtail REST API v2 at `/api/v2/`
- **Auth**: Social auth + OAuth2 toolkit + custom User model (`users.User`)
- **Settings**: Single file `mitxpro/settings.py`, env-var driven via `mitol.common.envs` helpers (`get_string()`, `get_bool()`, `get_int()`)
- **Feature flags**: PostHog via `mitxpro/features.py`

### Key Django Apps

| App              | Purpose                                                                                                      |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| `courses`        | Courses, programs, enrollments, certificates, runs                                                           |
| `cms`            | Wagtail CMS pages + REST API — see [cms/README.md](cms/README.md)                                            |
| `ecommerce`      | Orders, products, coupons, CyberSource payments, tax                                                         |
| `b2b_ecommerce`  | B2B ordering and enrollment                                                                                  |
| `courseware`     | Open edX integration, user sync, API tokens                                                                  |
| `sheets`         | Google Sheets automation for enrollment codes, refunds, deferrals — see [sheets/README.md](sheets/README.md) |
| `authentication` | OAuth2, social auth pipelines, JWT (djoser)                                                                  |
| `users`          | Custom User model                                                                                            |
| `compliance`     | Audit logging, data consent                                                                                  |
| `mail`           | Email templates, Mailgun integration                                                                         |
| `hubspot_xpro`   | HubSpot CRM sync                                                                                             |

## Build and Test

### Python

```sh
uv run pytest                              # Run all tests (with coverage)
uv run pytest path/to/test_file.py -k test_name  # Run specific test
uv run ./scripts/test/python_tests.sh      # Full suite (migration checks + tests)
uv run ./scripts/test/detect_missing_migrations.sh
pre-commit run --all-files                 # Ruff, shfmt, yamllint, detect-secrets
```

### JavaScript

```sh
npm run test          # Mocha tests
npm run lint-check    # ESLint
npm run lint-fix      # ESLint auto-fix
npm run fmt           # Prettier format
npm run fmt:check     # Prettier check
npm run flow          # Flow type check
npm run scss-lint     # SCSS lint
```

### Docker (primary dev environment)

```sh
docker-compose up                                    # Start all services
docker-compose run --rm web pytest                   # Tests in container
docker-compose run --rm watch npm run lint-check     # JS lint in container
```

Services: `db` (:5432), `redis` (:6379), `web` (:8051), `watch` (:8052), `nginx` (:8053), `celery`

## Code Style

- **Python**: Ruff (formatting + linting via pre-commit). No additional config needed — pre-commit handles it.
- **JavaScript**: ESLint (`eslint-config-mitodl`) + Prettier. Flow for type checking (not TypeScript).
- **SCSS**: Stylelint via `npm run scss-lint`.
- **Secrets**: `detect-secrets` baseline at `.secrets.baseline` — update baseline if adding test secrets.

## Conventions

### Project structure per app

```
app_name/
  models.py          # Django models
  api.py             # Business logic / service layer
  views.py           # DRF ViewSets and views
  serializers.py     # DRF serializers
  factories.py       # Factory Boy test factories (DjangoModelFactory)
  *_test.py          # Tests colocated (models_test.py, api_test.py, views_test.py)
  tasks.py           # Celery tasks (if any)
  constants.py       # App-level constants
  admin.py           # Django admin config
  migrations/        # Auto-generated Django migrations
```

### Testing

- Test files live alongside source: `models_test.py`, `api_test.py`, `views_test.py`
- Use **Factory Boy** for test data — factories in each app's `factories.py`
- Use `@pytest.mark.django_db` for database access
- Celery tasks are eager in tests (`CELERY_TASK_ALWAYS_EAGER=True`)
- Tests run in parallel with `pytest-xdist` in CI (`-n logical`)
- Root `conftest.py` sets up shared fixtures

### API patterns

- DRF ViewSets + Serializers with paginated responses (default 20/page)
- Business logic in `api.py`, not in views
- Wagtail content via REST API: `/api/v2/pages/?type=cms.CoursePage`

### Environment variables

- All config is env-var driven — never hardcode secrets or URLs
- Required: `MITXPRO_BASE_URL`, `SECRET_KEY`, `MITXPRO_ENVIRONMENT`
- Access via `mitol.common.envs`: `get_string("VAR_NAME", "default")`

### Dependencies

- **Python**: Managed with `uv` — `uv sync --frozen` (lockfile: `uv.lock`)
- **Node**: Managed with `yarn` — `yarn install --immutable` (lockfile: `yarn.lock`)

### Issue and PR management

All issue and pull request templates are centralized in the [mitodl/.github](https://github.com/mitodl/.github) repository. Use those templates when creating issues or PRs.

## Further Reading

- [docs/rfcs/](docs/rfcs/) — Architecture decision records (ecommerce, auth, course data)
- [courses/docs/external-course-sync.md](courses/docs/external-course-sync.md) — External course sync
- [docs/configure_digital_credentials.md](docs/configure_digital_credentials.md) — Digital credentials setup
