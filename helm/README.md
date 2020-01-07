Deploy a Nextflow-API Server to Kubernetes Using Helm 
===

This guide assumes you have access to a K8s cluster, and either a valid PVC or storage class on that cluster.

#### 0. Install Helm 3 

Go to the [Helm Release Page](https://github.com/helm/helm/releases) and download the lastest release that begins with **Helm v3.x.x**. Follow the installation instructions.

Helm 3 is used because it does not require installing anything on the K8s cluster, while Helm 2 requires the user to install Tiller. This chart should work with Helm 2 if needed. 

#### 0.5 Create NFS Storage Class(optional) 

Nextflow-API requires persisitant storage to hold workflow data. If you already have access to a persistent volume claim(PVC), then you can use that one.

If not, you will need a valid storage class for the dynamic creation of a persistent volume claim(PVC).

To create a NFS storage provisioner under the *nfs* storage class: 

Update Helm's repositories: `helm repo update`

Install the NFS provisioner. Replace `<size>`(ex. 10Gi) with the maximum amount of storage you wish to allocate:

`helm install kf stable/nfs-server-provisioner \`

`--set=persistence.enabled=true,persistence.storageClass=standard,persistence.size=<size>`

Check that the `nfs` storage class exists:

`kubectl get sc` 


#### 1. Configure Nextflow-API Server

The file `values.yaml` contains all of the configurable values across the chart. 

Edit the following values:

##### PVC
```
# PVC
NewLocalPVC:
  # If true, create new PVC on local cluster.
  # (temp, future PVCs will be dynamically configurable)
  Enabled: true
  Name: nextflow-api-local
  Size: 20Gi
  StorageClass: nfs

ExistingLocalPVC:
  # If true, use existing PVC on local cluster.
  # (temp, future PVCs will be dynamically configurable)
  Enabled: false
  Name: deepgtex-prp
```

If you want to dynamically create a PVC:

1. Set NewLocalPVC to "True" and ExistingLocalPVC to "False"
2. Change the "Name" to the PVC you have set up on your K8s cluster.
3. Change the "StorageClass" and "Size" to whatever storage class and size you want to use.

If you want to use an existing PVC:

1. Set NewLocalPVC to "False" and ExistingLocalPVC to "True"
2. Change the "Name" to the PVC you have set up on your K8s cluster.

##### Resources/Replicas

```
# Resource request per container
Resources:
  CPU: 250m
  Memory: 1Gi

# Number of containers
Replicas: 1
```

You may change the resource requests to your liking. Leave the number of replicas alone for now.

##### Ingress 

```
# Ingress control settings
Ingress:
  # If true, use ingress control.
  # Otherwise, generic LoadBalancer networking will be used, 
  # and the other settings in this section will be ignored.
  Enabled: false
  # The subdomain to associate with this service.
  # This will result in a FQDN like {subdomain}.{cluster}.slateci.net
  Host: nextflow-api.nautilus.optiputer.net
  # The class of the ingress controller to use. 
  # For SLATE this should be 'slate'. 
  Class: traefik
```

Nextflow-API uses a LoadBalancer by default. To use an Ingress:

1. Change Enabled to "True"
2. Change the Host to "nextflow-api" + a valid DNS address.
3. Change the Class if needed.

Now the server is configured and ready for deployment!

#### 2.5 Remote Cluster Configuration

Nextflow-API now has the ability to run on one cluster and submit workflows to another!

Currently, you submit your kubeconfig as a secret(or SLATE secret) at runtime and select the context for the remote cluster of your choosing. When the workflow is submitted, input data is copied from the host cluster to the remote cluster, after the workflow has finished running the output is copied back to the host cluster.

To configure Nextflow-API to use a remote cluster:

0. Follow previous instructions up to this step. Currently, Nextflow-API still needs a PVC on the host cluster, so configuration is still the same up to this point.
1. Download kubeconfig for the remote cluster, the same way you would to access the cluster normally. Place the file in `~/.kube/config` just as you would normally. 
2. Run the script `nextflow-api/helm/gen-secret.sh` This script takes the config file at `~/.kube.config` and packages it as a Kubernetes [secret](https://kubernetes.io/docs/concepts/configuration/secret/). This allows you to securely pass your config file to the server.
3. Configure `values.yaml`. See the `remote` section:

```
# Remote cluster settings(temp, future will be dynamically configurable)
Remote:
  # If true, use PVC/compute of remote cluster.
  # Otherwise, PVC/compute of local cluster will be used.
  # (temp, future will be dynamically configurable)
  Enabled: false
  Context: nautilus
  PVC: deepgtex-prp
```

Set `Enabled` to `true`
Set `Context` to the context of the remote cluster. 

To find the context, run `kubectl config get-contexts`.

Set `PVC` to the PVC you want to use on the remote cluster. 

To find existing PVCs, run `kubectl get pvc`
 
4. Switch kubectl access back to the host cluster you wish to deploy Nextflow-API on. To do this, either replace the remote cluster's config with the hosts at `~/.kube/config`, or just switch back to the host cluster's context with `kubectl config use-context <host-cluster`.

5. Continue with the deployment instructions below! 


#### 2. Deploy Nextflow Server

Navigate to `nextflow-api/helm`

Deploy using `helm install nf .`

#### 3. Use Nextflow Server

**If this is a new cluster:**

Give Nextflow the necessary permissions to deploy jobs to your K8s cluster:

```
kubectl create rolebinding default-edit --clusterrole=edit --serviceaccount=default:default 
kubectl create rolebinding default-view --clusterrole=view --serviceaccount=default:default
```

##### LoadBalancer(default) or Ingress

Ingress: navigate to the host you specified.

Run `kubectl get svc` to get the service that is exposing your server to the internet.

Record the **External IP** for the service `nf-nextflow-api`.

Open an internet browser, then navigate to `<EXT_IP>:8080` 

You may create and submit workflows from there.

#### 4. Delete deployment

If you'd like to destroy, use `helm delete nf`.

All done!
