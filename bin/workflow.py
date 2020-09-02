#!/usr/bin/env python3

import asyncio
import os
import subprocess

import env



def run_workflow(workflow, work_dir, resume):
	# save current directory
	prev_dir = os.getcwd()

	# change to workflow directory
	os.chdir(work_dir)

	# launch workflow, wait for completion
	if env.NXF_EXECUTOR == 'k8s':
		args = [
			'nextflow',
			'-config', 'nextflow.config',
			'-log', os.path.join(workflow['output_dir'], 'nextflow.log'),
			'kuberun',
			workflow['pipeline'],
			'-ansi-log', 'false',
			'-latest',
			'-name', 'workflow-%s' % (workflow['_id']),
			'-profile', workflow['profiles'],
			'-revision', workflow['revision'],
			'-volume-mount', env.PVC_NAME
		]

	elif env.NXF_EXECUTOR == 'local':
		args = [
			'nextflow',
			'-config', 'nextflow.config',
			'-log', os.path.join(workflow['output_dir'], 'nextflow.log'),
			'run',
			workflow['pipeline'],
			'-ansi-log', 'false',
			'-latest',
			'-name', 'workflow-%s' % (workflow['_id']),
			'-profile', workflow['profiles'],
			'-revision', workflow['revision'],
			'-with-docker' if workflow['with_container'] else ''
		]

	elif env.NXF_EXECUTOR == 'pbspro':
		args = [
			'nextflow',
			'-config', 'nextflow.config',
			'-log', os.path.join(workflow['output_dir'], 'nextflow.log'),
			'run',
			workflow['pipeline'],
			'-ansi-log', 'false',
			'-latest',
			'-name', 'workflow-%s' % (workflow['_id']),
			'-profile', workflow['profiles'],
			'-revision', workflow['revision'],
			'-with-singularity' if workflow['with_container'] else ''
		]

	if resume:
		args.append('-resume')

	proc = subprocess.Popen(
		args,
		stdout=open('.workflow.log', 'w'),
		stderr=subprocess.STDOUT
	)

	# return to original directory
	os.chdir(prev_dir)

	return proc



def save_output(workflow, output_dir):
	return subprocess.Popen(['./scripts/kube-save.sh', workflow['_id'], output_dir])



async def set_property(db, workflow, key, value):
	workflow[key] = value
	await db.workflow_update(workflow['_id'], workflow)



async def launch_async(db, workflow, resume):
	# re-initialize database backend
	db.initialize()

	# start workflow
	work_dir = os.path.join(env.WORKFLOWS_DIR, workflow['_id'])
	proc = run_workflow(workflow, work_dir, resume)
	proc_pid = proc.pid

	print('%d: saving workflow pid...' % (proc_pid))

	# save workflow pid
	await set_property(db, workflow, 'pid', proc.pid)

	print('%d: waiting for workflow to finish...' % (proc_pid))

	# wait for workflow to complete
	if proc.wait() == 0:
		print('%d: workflow completed' % (proc_pid))
		await set_property(db, workflow, 'status', 'completed')
	else:
		print('%d: workflow failed' % (proc_pid))
		await set_property(db, workflow, 'status', 'failed')
		return

	print('%d: saving output data...' % (proc_pid))

	# save output data
	output_dir = os.path.join(env.WORKFLOWS_DIR, workflow['_id'], workflow['output_dir'])
	proc = save_output(workflow, output_dir)

	if proc.wait() == 0:
		print('%d: save output data completed' % (proc_pid))
	else:
		print('%d: save output data failed' % (proc_pid))



def launch(db, workflow, resume):
	asyncio.run(launch_async(db, workflow, resume))
