#!/bin/bash
#
# This script upgrades the data directory for the `db` container
# to the version specified in docker-compose.yml

function normalize_version() {
  major_version=$(echo $1 | cut -d'.' -f1)
  minor_version=$(echo $1 | cut -d'.' -f2)

  # versions above 9.x only use the major version
  if [[ "${major_version}" -gt "9" ]]
  then
    printf "${major_version}"
  else
    printf "${major_version}.${minor_version}"
  fi
}

TMP_DIR=$(mktemp -d)

echo "Using temp directory ${TMP_DIR}"

OLD_DIR="${TMP_DIR}/old/"
mkdir $OLD_DIR
chmod +rw $OLD_DIR

# copy the old data from the container to the temp directory
DB_CONTAINER_NAME=$(docker-compose ps --all | grep postgres | awk '{ print $1 }')
docker cp $DB_CONTAINER_NAME:/var/lib/postgresql/data $OLD_DIR

# the old version comes from the version the data directory was initialized with
OLD_VERSION=$(cat "${OLD_DIR}/data/PG_VERSION")

# the new version comes from the current container
NEW_VERSION=$(docker-compose run --rm db psql -V | head | awk '{ print $3 }')

# normalize the versions
OLD_VERSION=$(normalize_version $OLD_VERSION)
NEW_VERSION=$(normalize_version $NEW_VERSION)

# move the data dirs into versioned ones
mv $OLD_DIR "${TMP_DIR}/${OLD_VERSION}"
OLD_DIR="${TMP_DIR}/${OLD_VERSION}"
NEW_DIR="${TMP_DIR}/${NEW_VERSION}"

if [[ "${OLD_VERSION}" == "${NEW_VERSION}" ]]
then
  echo "Cannot upgrade: data version matches server version"
else
  echo "Upgrading ${OLD_VERSION} => ${NEW_VERSION}"
  docker run --rm \
    -v "${TMP_DIR}":/var/lib/postgresql \
    "tianon/postgres-upgrade:${OLD_VERSION}-to-${NEW_VERSION}" \
    --link

  # the above script changed ownership of everything to the container's `postgres user`
  # so change it back using that user - a bit of a hack, but it avoids `sudo`
  USER_ID=$(id -u)
  docker-compose run --rm -v "${TMP_DIR}":/var/lib/postgresql db chown ${USER_ID} -R /var/lib/postgresql/

  # this gets stripped in the upgrade for whatever reason
  echo "host all all 0.0.0.0/0 trust" >> "${NEW_DIR}/data/pg_hba.conf"

  # copy upgraded files into the container's data dir
  echo ""
  echo "Copying upgraded files back into container"
  docker cp "${NEW_DIR}/data/." "${DB_CONTAINER_NAME}:/var/lib/postgresql/data/"

  # done
  echo ""
  echo "Cleaning up"
  # rm -rf $TMP_DIR
  echo ""
  echo "Data has been upgraded to ${NEW_VERSION}"
fi
