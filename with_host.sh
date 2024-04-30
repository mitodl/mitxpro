#!/bin/bash
set -e

HOST_IP=$(netstat -nr | grep ^0\.0\.0\.0 | awk '{print $2}')
export HOST_IP

# Execute passed in arguments
# shellcheck disable=SC2068
$@
