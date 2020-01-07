## 2. Create Persistant Data Storage to Host Workflow Data

Now that you have a K8s cluster, it is time to access it from the VM.

First, tell the VM where to look for the Kubernetes configurtion file:

`echo 'export KUBECONFIG=~/Downloads/kubeconfig.yaml' >> ~/.bashrc && source ~/.bashrc`

Test your connection with:

`kubectl config current-context`

The output should match the name of your cluster.

Now it is time to provision a NFS server to store workflow data. We will streamline this process by using Helm.

Update Helm's repositories(similar to `apt-get update)`:

`helm repo update`

Next, install a NFS provisioner onto the K8s cluster to permit dynamic provisoning for 10Gb of persistent data:

`helm install kf stable/nfs-server-provisioner \`

`--set=persistence.enabled=true,persistence.storageClass=standard,persistence.size=10Gi`

Check that the `nfs` storage class exists:

`kubectl get sc`

Next, deploy a 8Gb Persistant Volume Claim(PVC) to the cluster:

`kubectl apply -f task-pv-claim.yaml`

Check that the PVC was deployed successfully:

`kubectl get pvc`

Finally, login to the PVC to get a shell, enabling you to view and manage files:

`nextflow kuberun login -v task-pv-claim`

**Open a new terminal window.**

## 3. Deploy Genomic Workflow to Your Cloud

**In a new terminal window....**

Go to the `techex-demo` folder:

`cd ~/Desktop/techex-demo`

Give Nextflow the necessary permissions to deploy jobs to your K8s cluster:

```
kubectl create rolebinding default-edit --clusterrole=edit --serviceaccount=default:default 
kubectl create rolebinding default-view --clusterrole=view --serviceaccount=default:default
```

Load the input data onto the PVC:

`./kube-load.sh task-pv-claim input`

Deploy KINC using `nextflow-kuberun`:

`nextflow kuberun systemsgenetics/kinc-nf -v task-pv-claim`

**The workflow should take about 10-15 minutes to execute.**

#### 4. Retrieve and Visualize Gene Co-expression Network

Copy the output of KINC from the PVC to your VM:

`./kube-save.sh task-pv-claim output`

Open Cytoscape. (Applications -> Other -> Cytoscape)

Go to your desktop and open a file browsing window, navigate to `~/Desktop/techex-demo/output/Yeast`.

Finally, drag the file `Yeast.net` from the file browser to Cytoscape!

The network should now be visualized! 

