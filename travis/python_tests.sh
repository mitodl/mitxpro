#!/usr/bin/env bash
status=0

function run_test {
    "$@"
    local test_status=$?
    if [ $test_status -ne 0 ]; then
        status=$test_status
    fi
    return $status
}

run_test black --check .
run_test pytest
run_test ./travis/codecov_python.sh
run_test ./scripts/test/detect_missing_migrations.sh
run_test ./scripts/test/no_auto_migrations.sh

exit $status
