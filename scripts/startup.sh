#!/bin/bash
# Startup script for kubernetes deployment.

# start mongodb service
service mongodb start

# initialize backups directory
BACKUPS="/workspace/_backups"

mkdir -p ${BACKUPS}

# restore database backup if present
LATEST=$(ls ${BACKUPS} | tail -n 1)

if [[ ! -z ${LATEST} ]]; then
	./scripts/db-restore.sh "${BACKUPS}/${LATEST}"
fi

# start web server
python3 bin/server.py
