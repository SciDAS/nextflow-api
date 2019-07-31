#!/bin/bash

# parse command-line arguments
if [[ $# != 4 ]]; then
	echo "usage: $0 <gke-project-id> <path-to-key-file> <cluster-id> <zone>"
	exit -1
fi

PROJECTID="$1"
KEYPATH="$2"
CLUSTERID="$3"
ZONE="$4"

kubectl create configmap nextflow-server-config --from-literal=project.id=${PROJECTID} --from-file=project.key=${KEYPATH} --from-literal=project.cluster=${CLUSTERID} --from-literal=project.zone=${ZONE}