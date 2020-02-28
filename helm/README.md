# Deploy Nextflow-API to Kubernetes Using Helm

This guide assumes you have access to a K8s cluster, and either a valid PVC or storage class on that cluster.

## Install Helm

Follow the [installation instructions](https://helm.sh/docs/intro/install) from the Helm documentation to install Helm. The Helm chart for Nextflow-API is confirmed to work on [Helm v3.0.0-beta3](https://github.com/helm/helm/releases/tag/v3.0.0-beta.3), but it is failing on many newer versions of Helm, so if you have issues deploying Nextflow-API then try using that exact version.

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

#### Database and Web Server Deployments
```
# Database deployment settings
Database:
  # Resource requests and limits per container
  Resources:
    Requests:
      CPU: 4
      Memory: 8Gi
    Limits:
      CPU: 8
      Memory: 16Gi

# Web server deployment settings
WebServer:
  # Number of containers
  Replicas: 1
  # Resource requests and limits per container
  Resources:
    Requests:
      CPU: 1
      Memory: 4Gi
    Limits:
      CPU: 1
      Memory: 4Gi
```

Nextflow-API contains a database deployment and a web server deployment, which can optionally include multiple replicas. Note that you must use a `LoadBalancer` in order to have multiple web server replicas.

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

#### Give Nextflow the necessary permissions to deploy jobs to your K8s cluster.
````
kubectl create rolebinding default-edit --clusterrole=edit --serviceaccount=default:default
kubectl create rolebinding default-view --clusterrole=view --serviceaccount=default:default
````

These commands give the default service account the ability to view and edit cluster resources. Nextflow driver pods use this account to deploy process pods. This creates rolebindings in the `default` namespace. If you are not in the default namespace, use `KUBE_EDITOR="nano" kubectl edit rolebinding <role-binding>`. Edit the `namespace` to the one you are using, then save.

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
