Deploy a Nextflow-API Server to Kubernetes Using Helm 
===

This guide assumes you have access to a K8s cluster. 

#### 0. Download Helm 3

Go to the [Helm Release Page](https://github.com/helm/helm/releases) and download the lastest release that begins with **Helm v3.x.x**. Follow the installation instructions.

Helm 3 is used because it does not require installing anything on the K8s cluster, while Helm 2 requires the user to install Tiller. This chart should work with Helm 2 if needed. 

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

**TODO:** Remote cluster configuration(disregard and leave "False" for now)

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

#### 2. Deploy Nextflow Server

Navigate to `nextflow-api/helm`

Deploy using `helm install nf .`

#### 3. Use Nextflow Server

If you are using an Ingress, navigate to the host you specified.

##### LoadBalancer(default)

Run `kubectl get svc` to get the service that is exposing your server to the internet.

Record the **External IP** for the service `nf-nextflow-api`.

Open an internet browser, then navigate to `<EXT_IP>:8080` 

You may create and submit workflows from there.

#### 4. Delete deployment

If you'd like to destroy, use `helm delete nf`.

All done!
