#!/bin/bash

docker build -t bentsherman/nextflow-api docker
docker push bentsherman/nextflow-api

helm uninstall nextflow-api
helm install nextflow-api ./helm
