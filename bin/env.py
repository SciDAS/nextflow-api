import os

# define environment variables
WORKFLOWS_DIRS = {
	'k8s':    '/workspace/_workflows',
	'local':  '_workflows',
	'pbspro': '_workflows'
}

NXF_EXECUTOR = os.environ.get('NXF_EXECUTOR')
NXF_EXECUTOR = NXF_EXECUTOR if NXF_EXECUTOR else 'local'

PVC_NAME = os.environ.get('PVC_NAME')

WORKFLOWS_DIR = WORKFLOWS_DIRS[NXF_EXECUTOR]

# validate environment variables
if NXF_EXECUTOR == 'k8s' and PVC_NAME is None:
	raise EnvironmentError('Using k8s executor but PVC is not defined')