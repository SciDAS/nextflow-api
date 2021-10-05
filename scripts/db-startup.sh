#!/bin/bash
# Startup script for kubernetes deployment.

# start mongodb service
mkdir -p /data/db
mkdir -p /var/log/mongodb

mongod \
    --fork \
    --dbpath /data/db \
    --logpath /var/log/mongodb/mongod.log \
    --bind_ip 0.0.0.0

# initialize backups directory
BACKUPS="/workspace/_backups"

mkdir -p ${BACKUPS}

# restore database backup if present
LATEST=$(ls ${BACKUPS} | tail -n 1)

if [[ ! -z ${LATEST} ]]; then
    scripts/db-restore.sh "${BACKUPS}/${LATEST}"
fi

# create cronjob to backup database daily
echo "00 06 * * * ${PWD}/scripts/db-backup.sh daily" | crontab -
