#!/bin/sh

export KUBE_CONFIG=$(cat ~/.kube/config | base64 | tr -d '\n')

cat > templates/secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: kubeconfig
type: Opaque
data:
  config: ${KUBE_CONFIG}
EOF

cat templates/secret.yaml
