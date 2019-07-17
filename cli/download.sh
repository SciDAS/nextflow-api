#!/bin/bash
# Download output data for a workflow instance on a nextflow server.

# parse command-line arguments
if [[ $# != 2 ]]; then
	echo "usage: $0 <url> <id>"
	exit -1
fi

URL="$1"
ID="$2"

# download output data for a workflow instance
curl -s -o "${ID}-output.tar.gz" ${URL}/api/workflows/${ID}/download

echo
