Nextflow on GKE
===

The major goals of this project is to **automate the execution of Nextflow workflows on GKE** and **enable interaction with workflows via REST API**. 

Currently, it supports the following API endpoints. 

| Endpoint                   | Method | Description                               |
|----------------------------|--------|-------------------------------------------|
| /workflow                  | POST   | Create a workflow run                         |
| /workflow/[wf-id]          | DELETE | Delete the workflow run                     |
| /workflow/[wf-id]/upload   | POST   | Upload input/config files of the workflow |
| /workflow/[wf-id]/launch   | POST   | Launch the workflow                       |
| /workflow/[wf-id]/log      | GET    | Get the log of the workflow run           |
| /workflow/[wf-id]/download | GET    | Download the output data as a `tar.gz` file                  |

### Lifecycle

First of all, the user calls the API to create a workflow run. Along with the API call, the user needs to provide the **UUID of the workflow run** and the **container image for the workflow**. Note that the API **do not** generate UUID for any workflow runs. The payload of the API call is as below.

```json
{
  "uuid": "<uuid>",
  "image": "systemsgenetics/KINC-nf"
} 
```

Then the user uploads the input and config files for the workflow run. **The API assumes the first file suffixed with `.config` as the Nextflow config file for the workflow run.** 

After the input and config files in place, the user can launch the workflow. The launch starts with uploading of the input files to `<uuid>/input` on the NFS service. The jobs running as distributed pods in GKE will read the input data from here, and work together in the dedicated workspace prefixed with `<uuid>`. 

Once the workflow being launched, the log will be available via the API. Ideally, higher-level services can call the API periodically to fetch the latest log of the workflow run. 

After the run is done, the user can call the API to download the output files. The output files are placed in `<uuid>/output` on the NFS service. The API will compress the directory as a `tar.gz` file for downloading. 

The user can call the API to delete the run and purge its data once done with it. 

