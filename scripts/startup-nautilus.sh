#!/bin/bash
# Startup script for Nautilus/Kubernetes environment.

# parse command-line arguments
if [[ $# == 1 ]]; then
    BACKEND="$1"
elif [[ $# == 2 ]]; then
    BACKEND="$1"
    KUBE_CONTEXT="$2"
else
	echo "usage: $0 <backend> [kube-context]"
	exit -1
fi

# start mongodb server
if [[ ${BACKEND} == "mongo" ]]; then
    scripts/db-startup.sh
fi

# configure kubectl context if specified
if [[ ! -z ${KUBE_CONTEXT} ]]; then
    scripts/kube-config.sh ${KUBE_CONTEXT}
fi

# start web server
export TF_CPP_MIN_LOG_LEVEL="3"

bin/server.py --backend=${BACKEND}
