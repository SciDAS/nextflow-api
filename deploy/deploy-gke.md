Deploy Nextflow Servers to GKE for Running Workflows
===

This guide assumes you have access to a GKE project, have created a K8s cluster, and set up a PVC. 

Refer to [these instructions](README.md). 

#### 0. Create Service Account and ConfigMap

Make sure `gcloud` is [properly installed and authenticated](https://cloud.google.com/deployment-manager/docs/step-by-step-guide/installation-and-setup). Also make sure you have the role of **Kubernetes Engine Admin**, which can be added in [IAM & admin](https://cloud.google.com/kubernetes-engine/docs/how-to/iam) by your Cloud administrator. If certain types of resources (e.g. GPU) are required, make sure the corresponding [quota](https://cloud.google.com/compute/quotas) is requested and approved in advance. 

You must create a Service Account for Nextflow to use. Follow the [instructions](https://cloud.google.com/iam/docs/creating-managing-service-accounts). Make sure the account has **Editor** permissions.

After creating the account, **download a credential key for it**. It is a JSON formatted key. 

Use a [JSON Formatter](https://jsonformatter.curiousconcept.com/) to flatten the text to a single line, using the **Compact** format. 

Paste the formatted JSON back into the file. The file should be one line now.

You must then create a ConfigMap to pass sensetive credentials into the container. To do this, you need 4 different things:
- Your GKE project ID.
- The path to the JSON key file.
- Your K8s cluster ID.
- The zone your cluster is based in.

After collecting this information, run [this script](create-config-map.sh):

'''./create-config-map.sh <gke-project-id> <path-to-key-file> <cluster-id> <zone>```

It should return successful creation output.

#### 1. Deploy Nextflow Servers

You now have everything you need to deploy Nextflow servers to your K8s cluster. 

To start, you must edit [04-nextflow-server-gke.yaml](04-nextflow-server-gke.yaml).

Edit the line ```claimName: <PVC>``` to be the name of the Persistent Volume Claim you created. It is at the bottom of the file. Edit resources/replicas as needed.

Next, deploy the container(s) with ```kubectl create -f 04-nextflow-server-gke.yaml```.

Check that the pod(s) are running.

#### 2. Expose Nextflow Server Deployment 

Now that you have a deployment, you must create a service to expose the deployment to the Internet.

Run ```kubectl expose deployment nextflow-server-deployment --type=LoadBalancer --name=nextflow-server-service```.

It should be successful.

Next, Get the EXTERNAL IP of the service by running ```kubectl get services nextflow-server-service```

```
NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)          AGE
nextflow-server-service   LoadBalancer   <CLUSTER_IP>    <EXT_IP>         8080:<NODE_PORT>/TCP   58m
```
Your Nextflow server(s) is/are accessible at http://<EXT_IP>:8080

#### 3. Create a Workflow using CLI commands

The deployment of Nextflow servers should now be accessible from anywhere. To test, let's create a workflow!

Run [nf-create.sh](../cli/nf-create.sh):

```./nf-create http://<EXT_IP>:8080 SystemsGenetics/KINC-nf```

You should get an assigned Workflow ID: ```{"id": "<WORKFLOW_ID>"}```

Use this ID to launch, query, and delete your workflow. Documentation on this process can be found [here](../README.md).

#### 4. Delete deployment

If you'd like to destroy

Delete the deployment with ```kubectl delete -f 04-nextflow-server-gke.yaml```.

Delete the load balancing service with ```kubectl delete service nextflow-server-service```.

Delete the ConfigMap with ```kubectl delete configmap nextflow-server-config```.

All done!
