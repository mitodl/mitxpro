#!/usr/bin/env bash
set -eo pipefail

echohighlight() {
	# shellcheck disable=SC2145
	echo -e "\x1b[32;1m$@\x1b[0m"
}

function run_test {
	# shellcheck disable=SC2145
	echohighlight "[TEST SUITE] $@"
	poetry run "$@"
}

run_test ./scripts/test/detect_missing_migrations.sh
run_test ./scripts/test/no_auto_migrations.sh
run_test ./scripts/test/openapi_spec_check.sh
run_test pytest

# shellcheck disable=SC2154
exit $status
