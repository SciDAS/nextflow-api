# Deploy Nextflow-API to Kubernetes Using Helm

This guide assumes you have access to a K8s cluster, and either a valid PVC or storage class on that cluster.

## Download Helm 3

Follow the [installation instructions](https://helm.sh/docs/intro/install) from the Helm documentation to install __Helm v3.x.x__.

Helm 3 is used because it does not require installing anything on the K8s cluster, while Helm 2 requires the user to install Tiller. This chart should work with Helm 2 if needed.

## Configure Nextflow-API Helm Chart

The file `values.yaml` contains all of the configurable values for the chart.

Edit the following sections:

#### PVC
```
# PVC
NewLocalPVC:
  # If true, create new PVC on local cluster.
  # (temp, future PVCs will be dynamically configurable)
  Enabled: true
  Name: nextflow-api-local
  StorageClass: nfs
  Size: 20Gi

ExistingLocalPVC:
  # If true, use existing PVC on local cluster.
  # (temp, future PVCs will be dynamically configurable)
  Enabled: false
  Name: deepgtex-prp
```

If you want to create a new PVC:

1. Set `NewLocalPVC` to `true` and `ExistingLocalPVC` to `false`
2. Change the `Name` to the PVC you have set up on your K8s cluster.
3. Change the `StorageClass` and `Size` to whatever storage class and size you want to use.

If you want to use an existing PVC:

1. Set `NewLocalPVC` to `false` and `ExistingLocalPVC` to `true`
2. Change the `Name` to the PVC you have set up on your K8s cluster.

__TODO__: Remote cluster configuration (disregard and leave `false` for now)

#### Resources, Replicas
```
# Resource request per container
Resources:
  Requests:
    CPU: 250m
    Memory: 1Gi
  Limits:
    CPU: 500m
    Memory: 2Gi

# Number of containers
Replicas: 1
```

You may change the resource requests/limits to your liking. Leave the number of replicas alone for now.

#### Ingress / LoadBalancer
```
# Ingress control settings
Ingress:
  # If true, use ingress control.
  # Otherwise, generic LoadBalancer networking will be used,
  # and the other settings in this section will be ignored.
  Enabled: false
  # The subdomain to associate with this service.
  Host: nextflow-api.nautilus.optiputer.net
  Class: traefik
```

Nextflow-API will either use an `Ingress` or a `LoadBalancer` to expose itself to the public Internet.

To use an `Ingress`:

1. Set `Enabled` to `true`
2. Change the `Host` to `nextflow-api.<domain>`. (ex. `nextflow-api.scigateway.net`)
3. Change the `Class` if needed.

To use a `LoadBalancer`, simply set `Enabled` to `false`

Now the Helm Chart is configured and ready to deploy!

## Deploy Nextflow-API

Navigate to `nextflow-api/helm`

Deploy using `helm install nextflow-api .`

## Use Nextflow-API

#### Ingress

If you are using an `Ingress`, simply navigate in your web browser to the `Host` that you specified.

#### LoadBalancer

If you are using a `LoadBalancer`:

1. Run `kubectl get service` to list the services that are running in your cluster.
2. Find the service named `nextflow-api` and record the `EXTERNAL-IP`.
3. Navigate in your web browser to `<EXTERNAL-IP>:8080`

All done! Now you can use Nextflow-API to submit and monitor workflows.

## Delete Deployment

To delete the deployment, run `helm uninstall nextflow-api`.
