#!/bin/bash
# Backup a database to an archive.

# parse command-line arguments
if [[ $# != 1 ]]; then
	>&2 echo "usage: $0 <type>"
	exit 1
fi

DATABASE="nextflow_api"
DUMP="dump"
BACKUPS="/workspace/_backups"
TYPE="$1"

# remove existing dump directory
rm -rf ${DUMP}

# dump database to dump directory
mongodump -d ${DATABASE} -o ${DUMP}

# create archive of dump directory
tar -czvf $(date +"${BACKUPS}/${TYPE}_%Y_%m_%d.tar.gz") ${DUMP}

# remove older archives of the same type
NUM_BACKUPS=$(ls ${BACKUPS}/${TYPE}_* | wc -l)
MAX_BACKUPS=10

if [[ ${NUM_BACKUPS} > ${MAX_BACKUPS} ]]; then
	rm -f "$(ls ${BACKUPS}/${TYPE}_* | head -n 1)"
fi
