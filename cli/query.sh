#!/bin/bash
# List all workflow instances on a nextflow server.

# parse command-line arguments
if [[ $# != 1 ]]; then
	echo "usage: $0 <url>"
	exit -1
fi

URL="$1"

# list all workflow instances
curl -s -X GET ${URL}/api/workflows

echo
