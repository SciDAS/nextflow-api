#!/bin/bash
# Get a workflow instance on a nextflow server.

# parse command-line arguments
if [[ $# != 2 ]]; then
	echo "usage: $0 <url> <id>"
	exit -1
fi

URL="$1"
ID="$2"

# get a workflow instance
curl -s -X GET ${URL}/api/workflows/${ID}

echo
