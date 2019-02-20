#!/usr/bin/env bash
set -e -o pipefail

PIP_OLD=$(mktemp)
PIP_NEW=$(mktemp)
VENV=$(mktemp -d)


pip freeze > $PIP_NEW
/usr/local/bin/pip freeze > $PIP_OLD
if ! cmp -s $PIP_OLD $PIP_NEW
then
  echo "requirements files differ from docker image pip environment. Running diff image-pip tox-pip:"
  diff $PIP_OLD $PIP_NEW
  exit 1
fi

rm $PIP_OLD
rm $PIP_NEW
rm -r $VENV
