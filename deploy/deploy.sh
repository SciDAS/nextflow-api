#!/bin/bash

docker build -t bentsherman/nextflow-api docker
docker push bentsherman/nextflow-api

kubectl delete -f deploy/003-nextflow-api.yaml
kubectl create -f deploy/003-nextflow-api.yaml
