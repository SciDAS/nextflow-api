# Nextflow API for Kubernetes

This repository contains the code for a REST API which automates the execution of Nextflow pipeliens on Kubernetes. The application is implemented via Python ([Tornado](https://www.tornadoweb.org/en/stable/)) and it can be deployed on any Kubernetes cluster with a Persistent Volume Claim (PVC).

## API Endpoints

| Endpoint                     | Method | Description                                 |
|------------------------------|--------|---------------------------------------------|
| /api/version                 | GET    | Get current API version                     |
| /api/workflows               | GET    | List all workflow instances                 |
| /api/workflows               | POST   | Create a workflow instance                  |
| /api/workflows/{id}          | GET    | Get a workflow instance                     |
| /api/workflows/{id}          | POST   | Update a workflow instance                  |
| /api/workflows/{id}          | DELETE | Delete a workflow instance                  |
| /api/workflows/{id}/upload   | POST   | Upload input files to a workflow instance   |
| /api/workflows/{id}/launch   | POST   | Launch a workflow instance                  |
| /api/workflows/{id}/log      | GET    | Get the log of a workflow instance          |
| /api/workflows/{id}/download | GET    | Download the output data as a `tar.gz` file |

## Lifecycle

First, the user calls the API to create a workflow instance. Along with the API call, the user must provide the __name of the Nextflow pipeline__. The payload of the API call is shown below.

```json
{
  "pipeline": "systemsgenetics/KINC-nf"
}
```

Then the user uploads the input files (including `nextflow.config`) for the workflow instance.

After the input and config files in place, the user can launch the workflow. The launch starts with uploading of the input files to `<id>/input` on the PVC. The jobs running as distributed pods in k8s will read the input data from here, and work together in the dedicated workspace prefixed with `<id>`.

Once the workflow is launched, the status and log will be available via the API. Ideally, higher-level services can call the API periodically to fetch the latest log of the workflow instance.

After the run is done, the user can call the API to download the output files. The output files are placed in `<id>/output` on the PVC. The API will compress the directory as a `tar.gz` file for downloading.

The user can call the API to delete the workflow instance and purge its data once done with it.

## Quickstart

To serve the API natively on a Ubuntu 18.04 LTS machine, use the commands below:

```console
$ sudo apt update && sudo apt install -y git python3 python3-pip \
  && git clone https://github.com/SciDAS/nextflow-api.git \
  && cd nextflow-api \
  && sudo pip3 install -r requirements.txt \
  && python3 server.py
The API is listening on http://0.0.0.0:8080
```

## Deployment

This repository provides a Dockerfile and YAML file for deploying the Nextflow API on a Kubernetes cluster. The dependencies can be seen in the Dockerfile. The API also assumes that __there is a PVC available__ with `ReadWriteMany` access. The PVC can be implemented in many ways; [here](deploy/README.md) we show how to set up the shared NFS storage in GKE, which is streamlined by Google to a certain extent. Additional knowledge about Kubernetes and NFS may be required to set up the NFS storage in a custom Kubernetes cluster.
