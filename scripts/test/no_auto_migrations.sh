#!/bin/bash

MIGRATIONS_OUTPUT=

fail() {
    echo "Error: migrations with generated names exist"
    echo $MIGRATIONS_OUTPUT
    exit 1
}

# search for auto migrations excluded the preexisting one
MIGRATIONS_OUTPUT="$(find */migrations/*_auto_*.py 2> /dev/null)"

if [[ $MIGRATIONS_OUTPUT != "" ]]
then
    fail
fi
