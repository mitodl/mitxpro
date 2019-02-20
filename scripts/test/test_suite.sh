#!/usr/bin/env bash
set -euf -o pipefail

docker-compose run web tox
docker-compose run watch npm run-script lint
docker-compose run watch npm run-script flow
docker-compose run watch npm run-script coverage
