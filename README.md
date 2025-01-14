# mitxpro

**SECTIONS**

1. [Initial Setup](#initial-setup)
2. [Optional Setup](#optional-setup)

# Initial Setup

mitxpro follows the same [initial setup steps outlined in the common ODL web app guide](https://mitodl.github.io/handbook/how-to/common-web-app-guide.html).
Run through those steps **including the addition of `/etc/hosts` aliases and the optional step for running the
`createsuperuser` command**.

### Configure xPro and Open edX

See Configure Open edX:

- [Using Tutor](https://github.com/mitodl/handbook/tree/master/openedx/MITx-edx-integration-tutor.md) (Recommended)
- [Using Devstack](https://github.com/mitodl/handbook/tree/master/openedx/MITx-edx-integration-devstack.md) (Deprecated)

### Add settings values

Add the following settings in your `.env` file:

```
MAILGUN_RECIPIENT_OVERRIDE=<your email address>

# Ask a fellow developer for these values
MAILGUN_SENDER_DOMAIN=
MAILGUN_KEY=
```

# Optional Setup

Described below are some setup steps that are not strictly necessary
for running the app

### Running tests

#### NOTE: These commands can be run with `docker-compose exec` to execute them in an already-running container, or with `docker-compose run --rm` to execute them in a new container.

    ### PYTHON TESTS/LINTING
    # Run Python tests

    docker-compose run --rm web pytest
    # Run Python tests in a single file
    docker-compose run --rm web pytest /path/to/test.py
    # Run Python test cases in a single file that match some function/class name
    docker-compose run --rm web pytest /path/to/test.py -k test_some_logic

    ### PYTHON FORMATTING
    # We have a Ruff hook in the pre-commit that checks and formats files wherever possible.
    pip install pre-commit
    pre-commit run --all-files

    ### JS/CSS TESTS/LINTING
    # We also include a helper script to execute JS tests in most of our projects
    docker-compose run --rm watch ./scripts/test/js_test.sh
    # Run JS tests in specific file
    docker-compose run --rm watch ./scripts/test/js_test.sh path/to/file.js
    # Run JS tests in specific file with a description that matches some text
    docker-compose run --rm watch ./scripts/test/js_test.sh path/to/file.js "should test basic arithmetic"
    # Run the JS linter
    docker-compose run --rm watch npm run lint
    # Run SCSS linter
    docker-compose run --rm watch npm run scss_lint
    # Run the Flow type checker
    docker-compose run --rm watch npm run-script flow

    # Run prettier-eslint, fixes style issues that may be causing the build to fail
    docker-compose run --rm watch npm run fmt

### Seed data

Seed data can be generated via management command. It's designed to be idempotent, so running it multiple times should not create multiple sets of data.
**NOTE:** If you have run `configure_instance` command, it will also create seed data, you don't need to run `seed_data` command again

```
docker-compose run --rm web ./manage.py seed_data
# To delete seed data
docker-compose run --rm web ./manage.py delete_seed_data
```

### Running the app in a notebook

This repo includes a config for running a [Jupyter notebook](https://jupyter.org/) in a
Docker container. This enables you to do in a Jupyter notebook anything you might
otherwise do in a Django shell. To get started:

- Copy the example file
  ```bash
  # Choose any name for the resulting .ipynb file
  cp localdev/app.ipynb.example localdev/app.ipynb
  ```
- Build the `notebook` container _(for first time use, or when requirements change)_
  ```bash
  docker-compose -f docker-compose-notebook.yml build
  ```
- Run all the standard containers (`docker-compose up`)
- In another terminal window, run the `notebook` container
  ```bash
  docker-compose -f docker-compose-notebook.yml run --rm --service-ports notebook
  ```
- Visit the running notebook server in your browser. The `notebook` container log output will
  indicate the URL and `token` param with some output that looks like this:
  ```
  notebook_1  |     To access the notebook, open this file in a browser:
  notebook_1  |         file:///home/mitodl/.local/share/jupyter/runtime/nbserver-8-open.html
  notebook_1  |     Or copy and paste one of these URLs:
  notebook_1  |         http://(2c19429d04d0 or 127.0.0.1):8080/?token=2566e5cbcd723e47bdb1b058398d6bb9fbf7a31397e752ea
  ```
  Here is a one-line command that will produce a browser-ready URL from that output. Run this in a separate terminal:
  ```bash
  APP_HOST="xpro.odl.local"; docker logs $(docker ps --format '{{.Names}}' | grep "_notebook_run_") | grep -E "http://(.*):8080[^ ]+\w" | tail -1 | sed -e 's/^[[:space:]]*//' | sed -e "s/(.*)/$APP_HOST/"
  ```
  OSX users can pipe that output to `xargs open` to open a browser window directly with the URL from that command.
- Navigate to the `.ipynb` file that you created and click it to run the notebook
- Execute the first block to confirm it's working properly (click inside the block
  and press Shift+Enter)

From there, you should be able to run code snippets with a live Django app just like you
would in a Django shell.

### Hubspot integration

- For testing/dev purposes, [create a sandbox account under your enterprise account](https://knowledge.hubspot.com/account/set-up-a-hubspot-standard-sandbox-account) if one doesn't exist yet.
- You will also need a [private app for your sandbox account](https://developers.hubspot.com/docs/api/migrate-an-api-key-integration-to-a-private-app)
  - Scopes:
    - CRM: everything except quotes and feedback
    - Standard: crm.export, crm.import, e-commerce, integration-sync
- Set `MITOL_HUBSPOT_API_PRIVATE_TOKEN` to the private app token in your .env file

## Commits

To ensure commits to github are safe, you should install the following first:

```
pip install pre_commit
pre-commit install
```

To automatically install precommit hooks when cloning a repo, you can run this:

```
git config --global init.templateDir ~/.git-template
pre-commit init-templatedir ~/.git-template
```

# Updating python dependencies

Python dependencies are managed with poetry. If you need to add a new dependency, run this command:

```
docker compose run --rm web poetry add <dependency>
```

This will update the `pyproject.toml` and `poetry.lock` files. Then run `docker-compose build web celery` to make the change permanent in your docker images.
Refer to the [poetry documentation](https://python-poetry.org/docs/cli/) for particulars about specifying versions, removing dependencies, etc.

# PostHog Integration

We are using PostHog for managing the features. PostHog provides many built-in filters/conditions to enable/disable features in the application without any code change or deployment.

_NOTE:_ We are using [olposthog](https://github.com/mitodl/ol-django/tree/main/src/olposthog) which is our own wrapper around PostHog to make things simpler and add caching.

You need below configurations in the application to use PostHog. Once enabled you can manage the feature flags through your PostHog account dashboard.

**\*(Required)**

- POSTHOG_ENABLED
- POSTHOG_PROJECT_API_KEY
- POSTHOG_API_HOST

**(Optional)**

- POSTHOG_FEATURE_FLAG_REQUEST_TIMEOUT_MS (`Default value: 3000`)
- POSTHOG_MAX_RETRIES (`Default value: 3`)
