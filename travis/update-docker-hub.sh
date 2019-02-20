#!/bin/bash
set -eo pipefail

export NEXT=$(date | md5sum | cut -c -6)
export PROJECT_NAME="mitxpro"
echo "Next hash is $NEXT"

export WEB_IMAGE=mitodl/${PROJECT_NAME}_web_travis_${NEXT}
export WATCH_IMAGE=mitodl/${PROJECT_NAME}_watch_travis_${NEXT}

echo docker build -t $WEB_IMAGE -f Dockerfile .
echo docker build -t $WATCH_IMAGE -f travis/Dockerfile-travis-watch-build .

echo docker push $WEB_IMAGE
echo docker push $WATCH_IMAGE

sed -i "s/^FROM mitodl\/.+$/$WEB_IMAGE/" travis/Dockerfile-travis-web
sed -i "s/^FROM mitodl\/.+$/$WATCH_IMAGE/" travis/Dockerfile-travis-watch
