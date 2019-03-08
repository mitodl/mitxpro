#!/bin/bash

MIGRATIONS_OUTPUT=

fail() {
    echo "Error: one or more migrations are missing"
    echo $MIGRATIONS_OUTPUT
    exit 1
}

MIGRATIONS_OUTPUT="$(./manage.py makemigrations --no-input --dry-run 2>&1)"
if [[ $? -ne 0 ]]
then
    # makemigrations has returned a non-zero for some reason, possibly
    # because it needs input but --no-input is set
    fail
elif [[ $(echo "$MIGRATIONS_OUTPUT" | grep "No changes detected" | wc -l) -eq 0 ]]
then
    fail
fi
