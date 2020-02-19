# nextflow-api

Nextflow-API is a web application and REST API for submitting and monitoring Nextflow pipelines on a Kubernetes cluster. The application is implemented in Python using the ([Tornado](https://www.tornadoweb.org/en/stable/)) framework and it can be deployed on any Kubernetes cluster that supports Persistent Volume Claims (PVCs).

## Quickstart

Refer to the [Dockerfile](docker/Dockerfile) to see how to install Nextflow-API locally for testing.

## Deployment

Refer to the [helm](helm/README.md) for instructions on how to deploy Nextflow-API to a Kubernetes cluster.

## Usage

The core of Nextflow-API is a REST API which provides an interface to run Nextflow pipelines on a Kubernetes cluster. Nextflow-API provides a collection of [CLI scripts](cli) to demonstrate how to use the API, as well as a web interface for end users.

## API Endpoints

| Endpoint                       | Method | Description                                 |
|--------------------------------|--------|---------------------------------------------|
| `/api/workflows`               | GET    | List all workflow instances                 |
| `/api/workflows`               | POST   | Create a workflow instance                  |
| `/api/workflows/{id}`          | GET    | Get a workflow instance                     |
| `/api/workflows/{id}`          | POST   | Update a workflow instance                  |
| `/api/workflows/{id}`          | DELETE | Delete a workflow instance                  |
| `/api/workflows/{id}/upload`   | POST   | Upload input files to a workflow instance   |
| `/api/workflows/{id}/launch`   | POST   | Launch a workflow instance                  |
| `/api/workflows/{id}/log`      | GET    | Get the log of a workflow instance          |
| `/api/workflows/{id}/download` | GET    | Download the output data as a tarball       |
| `/api/tasks`                   | GET    | List all tasks                              |
| `/api/tasks`                   | POST   | Save a task (used by Nextflow)              |

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
