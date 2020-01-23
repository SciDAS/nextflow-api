#!/bin/bash
# Restore a database from an archive

# parse command-line arguments
if [[ $# != 1 ]]; then
	>&2 echo "usage: $0 <archive>"
	exit 1
fi

ARCHIVE="$1"
DUMP="dump"
DATABASE="nextflow_api"

# remove existing dump directory
rm -rf ${DUMP}

# extract archive to dump directory
tar -xvf ${ARCHIVE}

# restore database from archive
mongorestore --drop --nsInclude ${DATABASE}.* --noIndexRestore ${DUMP}
