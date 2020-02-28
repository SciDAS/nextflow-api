#!/bin/bash
# Startup script for kubernetes deployment.

# start mongodb service
mkdir -p /data/db
mkdir -p /logs
touch /logs/log.txt
mongod --fork --logpath /logs/log.txt --bind_ip 0.0.0.0

# initialize backups directory
BACKUPS="/workspace/_backups"

mkdir -p ${BACKUPS}

# restore database backup if present
LATEST=$(ls ${BACKUPS} | tail -n 1)

if [[ ! -z ${LATEST} ]]; then
    ./scripts/db-restore.sh "${BACKUPS}/${LATEST}"
fi
