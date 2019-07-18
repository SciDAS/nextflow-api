#!/bin/bash
# Create a workflow instance on a nextflow server.

# parse command-line arguments
if [[ $# != 2 ]]; then
	echo "usage: $0 <url> <pipeline>"
	exit -1
fi

URL="$1"
PIPELINE="$2"

# create a workflow instance
curl -s \
	-X POST \
	-d "{\"pipeline\":\"${PIPELINE}\"}" \
	${URL}/api/workflows/0

echo
