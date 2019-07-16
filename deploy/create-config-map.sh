#!/bin/bash

# parse command-line arguments
if [[ $# != 3 ]]; then
	echo "usage: $0 <gke-project-id> <path-to-key-file> <cluster-id>"
	exit -1
fi

PROJECTID="$1"
KEYPATH="$2"
CLUSTERID="$3"

kubectl create configmap nextflow-server-config --from-literal=project.id=${PROJECTID} --from-file=project.key=${KEYPATH} --from-literal=project.cluster=${CLUSTERID}