import os

# load settings from environment variables
NXF_EXECUTOR = os.environ.get('NXF_EXECUTOR', default='local')
PVC_NAME = os.environ.get('PVC_NAME')

# define working directories
BASE_DIRS = {
	'k8s':    '/workspace',
	'local':  '.',
	'pbspro': '.'
}
BASE_DIR = BASE_DIRS[NXF_EXECUTOR]

MODELS_DIR = os.path.join(BASE_DIR, '_models')
TRACE_DIR = os.path.join(BASE_DIR, '_trace')
WORKFLOWS_DIR = os.path.join(BASE_DIR, '_workflows')

# validate environment settings
if NXF_EXECUTOR == 'k8s' and PVC_NAME is None:
	raise EnvironmentError('Using k8s executor but PVC is not defined')