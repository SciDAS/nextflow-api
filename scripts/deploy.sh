#!/bin/bash

IMAGE_NAME="bentsherman/nextflow-api"

set -ex

# remove data files
rm -rf _models _trace _workflows .nextflow* db.json db.pkl

# build docker image
docker build -t ${IMAGE_NAME} .
docker push ${IMAGE_NAME}

# deploy helm chart to kubernetes cluster
helm uninstall nextflow-api
helm install nextflow-api ./helm
