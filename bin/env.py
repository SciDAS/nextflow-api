import os

WORKFLOWS_DIRS = {
	"k8s": "/workspace/_workflows",
	"local": "./_workflows",
	"pbspro": "./_workflows"
}

NXF_EXECUTOR = os.environ.get("NXF_EXECUTOR")
NXF_EXECUTOR = NXF_EXECUTOR if NXF_EXECUTOR else "local"

PVC_NAME = os.environ.get("PVC_NAME", "deepgtex-prp")

WORKFLOWS_DIR = WORKFLOWS_DIRS[NXF_EXECUTOR]
