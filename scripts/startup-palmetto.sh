#!/bin/bash
# Startup script for Palmetto environment.

# load modules
module purge
module load anaconda3/5.1.0-gcc/8.3.1
module load nextflow/20.07.1

# initialize environment
source activate nextflow-api

# start mongodb server
killall mongod

mongod \
    --fork \
    --dbpath /mongo/${USER}/data \
    --logpath /mongo/${USER}/mongod.log \
    --bind_ip_all

# start web server
export NXF_EXECUTOR="pbspro"
export TF_CPP_MIN_LOG_LEVEL="3"

bin/server.py --backend=mongo
