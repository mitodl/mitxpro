# mitxpro
 

## Major Dependencies
- Docker
  - OSX recommended install method: [Download from Docker website](https://docs.docker.com/mac/)
- docker-compose
  - Recommended install: pip (`pip install docker-compose`)
- Virtualbox (https://www.virtualbox.org/wiki/Downloads)
- _(OSX only)_ Node/NPM, and Yarn
  - OSX recommended install method: [Installer on Node website](https://nodejs.org/en/download/)
  - No specific version has been chosen yet.

## (OSX only) Getting your machine Docker-ready

#### Create your docker container:

The following commands create a Docker machine named ``mitxpro``, start the
container, and configure environment variables to facilitate communication
with the edX instance.

    docker-machine create --driver virtualbox mitxpro
    docker-machine start mitxpro
    # 'docker-machine env (machine)' prints export commands for important environment variables
    eval "$(docker-machine env mitxpro)"


## Docker Container Configuration and Start-up

#### 1) Create your ``.env`` file

This file should be copied from the example in the codebase:

    cp .env.example .env

#### 2) _(OSX only)_ Set up and run the webpack dev server on your host machine

In the development environment, our static assets are served from the webpack
dev server. When this environment variable is set, the script sources will
look for the webpack server at that host instead of the host where Docker is running.

You'll need to install the [yarn](https://yarnpkg.com/en/docs/cli/)
package manager. You can do:

    sudo node ./scripts/install_yarn.js

To install it. Nice! You can check which version is installed in
`package.json` to be make you're getting the version we are
standardized on.

Now, in a separate terminal tab, use the webpack helper script to install npm modules and run the dev server:

    ./webpack_dev_server.sh --install

The ``--install`` flag is only needed if you're starting up for the first time, or if updates have been made
to the packages in ``./package.json``. If you've installed those packages and there are no ``./package.json``
updates, you can run this without the ``--install`` flag: ``./webpack_dev_server.sh``

**DEBUGGING NOTE:** If you see an error related to node-sass when you run this script, try running
``yarn install`` again.

#### 3) Build the containers
Run this command:

    docker-compose build

You will also need to run this command whenever ``requirements.txt`` or ``test_requirements.txt`` change.

#### 4) Run migrations
Create the database tables from the Django models:

    docker-compose run web ./manage.py migrate

#### 5) Run the container

Start Django, PostgreSQL, and other related services:

    docker-compose up

In another terminal tab, navigate to the mitxpro directory
and add a superuser in the now-running Docker container:

    docker-compose run web ./manage.py createsuperuser

You should now be able to do the following:

1. Visit mitxpro in your browser on port `8053`. _(OSX Only)_ Docker auto-assigns
 the container IP. Run ``docker-machine ip`` to see it. Your mitxpro URL will
 be something like this: ``192.168.99.100:8053``.

## Running Commands and Testing

As shown above, manage commands can be executed on the Docker-contained
mitxpro app. For example, you can run a Python shell with the following command:

    docker-compose run web ./manage.py shell

Tests should be run in the Docker container, not the host machine. They can be run with the following commands:

    # Run the full suite
    ./test_suite.sh
    # Run Python tests only
    docker-compose run web tox
    # Single file test
    docker-compose run web tox /path/to/test.py
    # Run the JS tests with coverage report
    docker-compose run watch npm run-script coverage
    # run the JS tests without coverage report
    docker-compose run watch npm test
    # run a single JS test file
    docker-compose run watch npm run-script singleTest /path/to/test.js
    # Run the JS linter
    docker-compose run watch npm run-script lint
    # Run JS type-checking
    docker-compose run watch npm run-script flow
    # Run SCSS linter
    docker-compose run watch npm run scss_lint

Note that running [`flow`](https://flowtype.org) may not work properly if your
host machine isn't running Linux. If you are using a Mac, you'll need to run
`flow` on your host machine, like this:

    yarn install --frozen-lockfile
    npm run-script flow
