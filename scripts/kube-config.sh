#!/bin/bash
# Configure kubectl to use a given context on startup.

# parse command-line arguments
if [[ $# != 1 ]]; then
	echo "usage: $0 <kube-context"
	exit -1
fi

KUBE_CONTEXT="$1"

# configure kubectl context
cp -R /etc/.kube /root
kubectl config --kubeconfig=/root/.kube/config use-context ${KUBE_CONTEXT}