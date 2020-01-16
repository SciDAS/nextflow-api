#!/bin/bash
# Cancel a workflow instance on a nextflow server.

# parse command-line arguments
if [[ $# != 2 ]]; then
	echo "usage: $0 <url> <id>"
	exit -1
fi

URL="$1"
ID="$2"

# cancel a workflow instance
curl -s -X POST ${URL}/api/workflows/${ID}/cancel

echo
