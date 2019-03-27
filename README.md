# mitxpro

**SECTIONS**
1. [Initial Setup](#initial-setup)
1. [Optional Setup](#optional-setup)

# Initial Setup

mitxpro follows the same [initial setup steps outlined in the common ODL web app guide](https://github.com/mitodl/handbook/blob/master/common-web-app-guide.md).
Run through those steps **including the addition of `/etc/hosts` aliases and the optional step for running the
`createsuperuser` command**.

### Configure xPro and Open edX

1. See [Configure Open edX](docs/configure_open_edx.md)
1. Add an alias to `/etc/hosts` for Open edX. We have standardized this alias
  to `edx.odl.local`. Your `/etc/hosts` entry should look like this:

    ```
    127.0.0.1       edx.odl.local
    ```

### Add settings values

Add the following settings in your `.env` file:

```
MAILGUN_RECIPIENT_OVERRIDE=<your email address>

# Ask a fellow developer for these values
MAILGUN_SENDER_DOMAIN=
MAILGUN_KEY=
```

OS-specific settings to add to your `.env` file:

```
### Linux
# EDX_IP should be something like 172.22.0.1
OPENEDX_API_BASE_URL=http://$EDX_IP:18000

### OSX
OPENEDX_API_BASE_URL=http://docker.for.mac.localhost:18000
OPENEDX_BASE_REDIRECT_URL=http://edx.odl.local:18000
```

# Optional Setup

Described below are some setup steps that are not strictly necessary
for running the app

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

### Running tests

Unlike our other web applications this project is not using tox. To run tests locally, run this command instead:

    docker-compose run --rm web pytest
    
### Seed data

Seed data can be generated via management command. It's designed to be idempotent, so running it multiple times should not create multiple sets of data.

```
docker-compose run --rm web ./manage.py seed_data
# To delete seed data
docker-compose run --rm web ./manage.py seed_data --delete
```
