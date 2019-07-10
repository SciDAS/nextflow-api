Deploy GKE for Running Nextflow Workflow
===

#### 0. GCP and GKE authentication 

Make sure `gcloud` is [properly installed and authenticated](https://cloud.google.com/deployment-manager/docs/step-by-step-guide/installation-and-setup). Also make sure you have the role of **Kubernetes Engine Admin**, which can be added in [IAM & admin](https://cloud.google.com/kubernetes-engine/docs/how-to/iam) by your Cloud administrator. If certain types of resources (e.g. GPU) are required, make sure the corresponding [quota](https://cloud.google.com/compute/quotas) is requested and approved in advance. 

#### 1. Create GKE cluster
```bash
$ gcloud container clusters create \
> --machine-type <machine-type>
> --num-nodes <num-nodes> \
> [--preemptible \]
> [--zone <zone> \]
> [--accelerator type=<gpu-type>,count=<gpu-count> \]
> --cluster-version latest \
> [--enable-autoscaling --min-nodes <min-nodes> --max-nodes <max-nodes> \]
<cluster-name> 
```

(Optional) If the workflow requires GPU-enabled nodes, GPU units can be attached using the `--accelerator` option followed by the **type** and **count of GPUs per node**. The availability of different types of GPUs varies among regions, which can be found in Cloud IAM Quotas. Note that `count` means the count of GPUs per node, i.e. `[total # of GPUs] = [num-nodes] * [count]`. 

(Optional) If the workflow is **fault-tolerant**, `--preemptible` allows the workflow to use preemptible nodes, which is much less expensive as compared to the on-demand ones. 

#### 2. Connect `kubectl` to the cluster

Make sure you already have `kubectl` installed. On Ubuntu 18.04 LTS, you may use the following command to install it. 

```bash 
$ sudo snap install kubectl --classic 
```

Then you need to authenticate your `kubectl` to connect to the GKE cluster using the following command.

```bash
$ gcloud container clusters get-credentials <cluster-name>
```

#### 3. (Optional) Install GPU device drivers
If GPU-enabled nodes being used, the device drivers need to be installed in order to let the pods consume the GPU resources. GCP provides a simple way to install the drivers using `kubectl` as below. 

For Container-Optimized OS (COS):

```bash
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/stable/nvidia-driver-installer/cos/daemonset-preloaded.yaml
```

For Ubuntu:
```bash
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/ubuntu/daemonset-preloaded.yaml
```

#### 4. Set up the NFS service

NFS is used as the shared file system among the distributed nodes in the GKE cluster for data sharing. It serves as a Kubernetes service in GKE. To set up the service, we first need to create the persistent disk (PD) for storage. 

```bash 
$ gcloud compute disks crewate --size=<storage-size> [--zone <zone>] <pd-name>
```

After the PD being created, we then create the pod for it using [001-nfs-server.yaml](./001-nfs-server.yaml). **Note:** you need to replace the value of `pdName` (Line 33) with the name of newly created PD. 

```bash
$ kubectl apply -f 001-nfs-server.yaml
```

The next step is to expose the NFS pod as a Kubernetes service using [002-nfs-server-service.yaml](./002-nfs-server-service.yaml). 

```bash 
$ kubectl apply -f 002-nfs-server-service.yaml
```

Now we can find it listed as a service as below
```console
$ kubectl get svc
NAME         TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)                      AGE
kubernetes   ClusterIP   10.35.240.1   <none>        443/TCP                      4d21h
nfs-server   ClusterIP   10.35.247.9   <none>        2049/TCP,20048/TCP,111/TCP   4d21h
```

Then we need to export the NFS service as a persistent volume to the nodes in the cluster, so that the nodes can discover it and know how to mount it consistently among each other. We use the [003-pv-pvc.yaml](./003-pv-pvc.yaml) as below. **Note:** the value of `nfs.server` (Line 11) needs to be replaced with the `CLUSTER-IP` of the NFS service. 


#### 5. Install and configure Nextflow

Nextflow is dependent on Java 8+, so make sure JDK is properly installed. For example, you can install Java on Ubuntu 18.04 LTS as below.

```bash
$ sudo apt install -y default-jdk
```

Installing Nextflow is made simple with a one-liner.

```bash 
$ curl -s https://get.nextflow.io | bash
```

Before being able to run workflows, you needs to be authorized to submit workloads to the cluster. 

```bash
$ kubectl create rolebinding default-edit --clusterrole=edit --serviceaccount=default:default \
  && kubectl create rolebinding default-view --clusterrole=view --serviceaccount=default:default
```

#### 6. Run a test
```bash
$ ./nextflow kuberun nextflow-io/rnaseq-nf -v deepgtex-prp:$PWD
```


