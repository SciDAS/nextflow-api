#!/bin/bash
# Upload input data for a workflow instance on a nextflow server.

# parse command-line arguments
if [[ $# != 3 ]]; then
	echo "usage: $0 <url> <id> <filename>"
	exit -1
fi

URL="$1"
ID="$2"
FILENAME="$3"

# upload data to a workflow instance
curl -s \
	-F "filename=$(basename FILENAME)" \
	-F "body=@${FILENAME}" \
	${URL}/api/workflows/${ID}/upload

echo
