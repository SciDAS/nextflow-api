#!/bin/bash
# Load input data to a Persistent Volume on a Kubernetes cluster. NF-API VERSION

# parse command-line arguments
if [[ $# != 3 ]]; then
	echo "usage: $0 <pvc-name> <local-path> <workflow_id>"
	exit -1
fi

PVC_NAME="$1"
PVC_PATH="/workspace/_workflows"
WORKFLOW_ID="$3"
POD_FILE="pod.yaml"
POD_NAME="nf-api-load-$(printf %04x $RANDOM)"
LOCAL_PATH="$(realpath $2)"

# create pod config file
cat > $POD_FILE <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $POD_NAME
spec:
  containers:
  - name: $POD_NAME
    image: ubuntu
    args: ["sleep", "infinity"]
    volumeMounts:
    - mountPath: $PVC_PATH
      name: $PVC_NAME
  restartPolicy: Never
  volumes:
    - name: $PVC_NAME
      persistentVolumeClaim:
        claimName: $PVC_NAME
EOF

# create pod
kubectl create -f $POD_FILE

# wait for pod to initialize
POD_STATUS=""

while [[ $POD_STATUS != "Running" ]]; do
	sleep 1
	POD_STATUS="$(kubectl get pods --no-headers $POD_NAME | awk '{ print $3 }')"
	POD_STATUS="$(echo $POD_STATUS)"
done

# copy input data to pod
echo "creating dir..."
kubectl exec $POD_NAME -- bash -c "mkdir -p /workspace/_workflows/$WORKFLOW_ID"
echo "copying data..."
kubectl cp "$LOCAL_PATH" "$POD_NAME:/workspace/_workflows/$WORKFLOW_ID"
# temporary workaround
kubectl exec $POD_NAME -- bash -c "mv /workspace/$WORKFLOW_ID/(basename $LOCAL_PATH) /workspace/_workflows/$WORKFLOW_ID/(basename $LOCAL_PATH)  && rm -rf /workspace/$WORKFLOW_ID"

# delete pod
kubectl delete -f $POD_FILE
rm -f $POD_FILE
