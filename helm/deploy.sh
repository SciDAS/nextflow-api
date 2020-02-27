#!/bin/bash

docker build -t bentsherman/nextflow-db docker/nextflow-db
docker push bentsherman/nextflow-db

docker build -t bentsherman/nextflow-api docker/nextflow-api
docker push bentsherman/nextflow-api

helm uninstall nextflow-api
helm install nextflow-api ./helm
