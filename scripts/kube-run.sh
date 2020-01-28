#!/bin/bash
# Run a nextflow pipeline on a Kubernetes cluster.

# parse command-line arguments
if [[ $# -lt 3 ]]; then
	echo "usage: $0 <pvc-name> <id> <pipeline> [options]"
	exit -1
fi

PVC_NAME="$1"
ID="$2"
PIPELINE="$3"

shift 3
OPTIONS="$*"

POD_NAME="nextflow-api-${ID}"
SPEC_FILE="${POD_NAME}.yaml"
PVC_PATH="/workspace"

# write pod spec to file
cat > ${SPEC_FILE} <<EOF
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: nextflow
  name: ${POD_NAME}
spec:
  containers:
  - name: ${POD_NAME}
    image: nextflow/nextflow:${NXF_VER}
    imagePullPolicy: IfNotPresent
    env:
    - name: NXF_WORK
      value: ${PVC_PATH}/_workflows/${ID}/work
    - name: NXF_ASSETS
      value: ${PVC_PATH}/projects
    - name: NXF_EXECUTOR
      value: k8s
    - name: NXF_ANSI_LOG
      value: "false"
    command:
    - /bin/bash
    - -c
    - cd ${PVC_PATH}/_workflows/${ID}; nextflow run ${PIPELINE} ${OPTIONS}
    resources:
      requests:
        cpu: 1
        memory: 4Gi
    volumeMounts:
    - name: vol-1
      mountPath: ${PVC_PATH}
  restartPolicy: Never
  volumes:
  - name: vol-1
    persistentVolumeClaim:
      claimName: ${PVC_NAME}
EOF

# create pod
kubectl create -f ${SPEC_FILE}

# wait for pod to initialize
POD_STATUS=""

while [[ ${POD_STATUS} != "Running" ]]; do
	sleep 2
	POD_STATUS="$(kubectl get pod --no-headers --output jsonpath={.status.phase} ${POD_NAME})"
done

# stream output log
kubectl logs -f ${POD_NAME}

# delete pod
kubectl delete -f ${SPEC_FILE}

# cleanup
rm -f ${SPEC_FILE}
