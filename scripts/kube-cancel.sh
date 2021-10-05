#!/bin/bash
# Remove all pods associated with a given workflow run.

# parse command-line arguments
if [[ $# != 1 ]]; then
	echo "usage: $0 <run-name>"
	exit -1
fi

RUN_NAME="$1"

# query list of pods
PODS=`kubectl get pods --output custom-columns=NAME:.metadata.name,RUN:.metadata.labels.runName \
	| grep ${RUN_NAME} \
	| awk '{ print $1 }'`

# delete pods
if [[ ! -z ${PODS} ]]; then
	kubectl delete pods ${PODS}
fi
