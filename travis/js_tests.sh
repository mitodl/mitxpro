#!/usr/bin/env bash
status=0

echohighlight() {
  echo -e "\033[1;92m$@\e[0m"
}

function run_test {
    echohighlight "[TEST SUITE] $@"
    "$@"
    local test_status=$?
    if [ $test_status -ne 0 ]; then
        status=$test_status
    fi
    echo ""
    return $status
}

run_test npm run codecov
run_test npm run lint
run_test npm run fmt:check
run_test npm run scss_lint
run_test npm run flow
run_test node node_modules/webpack/bin/webpack.js --config webpack.config.prod.js --bail

exit $status
