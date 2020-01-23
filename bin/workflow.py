#!/usr/bin/env python3

import json
import os
import subprocess
import sys



WORKFLOWS_DIRS = {
	"k8s": "/workspace/_workflows",
	"local": "./_workflows",
	"pbspro": "./_workflows"
}

NXF_EXECUTOR = os.environ.get("NXF_EXECUTOR")
NXF_EXECUTOR = NXF_EXECUTOR if NXF_EXECUTOR else "local"
PVC_NAME = os.environ.get("PVC_NAME", "deepgtex-prp")
WORKFLOWS_DIR = WORKFLOWS_DIRS[NXF_EXECUTOR]



def run_workflow(workflow, work_dir, resume):
	# save current directory
	prev_dir = os.getcwd()

	# change to workflow directory
	os.chdir(work_dir)

	# launch workflow, wait for completion
	if NXF_EXECUTOR == "k8s":
		args = [
			"/opt/nextflow-api/scripts/kube-run.sh",
			PVC_NAME,
			workflow["_id"],
			workflow["pipeline"],
			"-ansi-log", "false",
			"-latest",
			"-profile", workflow["profiles"],
			"-revision", workflow["revision"]
		]
	elif NXF_EXECUTOR == "local":
		args = [
			"nextflow",
			"-config", "nextflow.config",
			"run",
			workflow["pipeline"],
			"-ansi-log", "false",
			"-latest",
			"-profile", workflow["profiles"],
			"-revision", workflow["revision"],
			"-with-docker"
		]
	elif NXF_EXECUTOR == "pbspro":
		args = [
			"nextflow",
			"-config", "nextflow.config",
			"run",
			workflow["pipeline"],
			"-ansi-log", "false",
			"-latest",
			"-profile", workflow["profiles"],
			"-revision", workflow["revision"]
		]

	if resume:
		args.append("-resume")

	proc = subprocess.Popen(
		args,
		stdout=open(".workflow.log", "w"),
		stderr=subprocess.STDOUT
	)

	# return to original directory
	os.chdir(prev_dir)

	return proc



def save_output(workflow, output_dir):
	return subprocess.Popen(["./scripts/kube-save.sh", workflow["_id"], output_dir])



async def set_property(db, workflow, key, value):
	await db.workflows.update_one({ "_id": workflow["_id"] }, { "$set": { key: value } })



async def launch(db, workflow, resume):
	# start workflow
	work_dir = os.path.join(WORKFLOWS_DIR, workflow["_id"])
	proc = run_workflow(workflow, work_dir, resume)

	# save workflow pid
	await set_property(db, workflow, "pid", proc.pid)

	# wait for workflow to complete
	if proc.wait() != 0:
		await set_property(db, workflow, "status", "failed")
		return

	# save output data
	output_dir = os.path.join(WORKFLOWS_DIR, workflow["_id"], workflow["output_dir"])
	proc = save_output(workflow, output_dir)

	if proc.wait() != 0:
		await set_property(db, workflow, "status", "failed")
		return

	# save final status
	await set_property(db, workflow, "status", "completed")
