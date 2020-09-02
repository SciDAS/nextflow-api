#!/bin/bash
# configure kubectl to use a given context on startup

KUBE_CONTEXT="$1"

cp -R /etc/.kube /root
kubectl config --kubeconfig=/root/.kube/config use-context ${KUBE_CONTEXT}
kubectl get pods