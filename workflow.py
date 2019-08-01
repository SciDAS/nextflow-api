#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys



NEXTFLOW_K8S = True if os.environ.get("NEXTFLOW_K8S") else False
PVC_NAME = os.environ.get("PVC_NAME", "deepgtex-prp")
WORKFLOWS_DIR = "/workspace/_workflows" if NEXTFLOW_K8S else "./_workflows"



def run_cmd(args, log_file=None, debug=True):
	# run command as child process
	proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	# wait for command to finish
	while True:
		# read line from stdout
		line = proc.stdout.readline()

		# break if process is done
		if not line and proc.poll() is not None:
			break

		# write line to log file
		if line:
			if log_file:
				with open(log_file, "a") as f:
					f.write(str(line, "utf-8"))
					f.flush()

			if log_file is None or debug:
				sys.stdout.write("%d: %s" % (proc.pid, line.decode("ascii", "ignore")))
				sys.stdout.flush()

	return proc.returncode



def save_status(work_dir, status):
	workflow = json.load(open("%s/config.json" % work_dir))
	workflow["status"] = status

	json.dump(workflow, open("%s/config.json" % work_dir, "w"))



def run_workflow(pipeline, profiles, resume, revision, work_dir, log_file):
	# save current directory
	prev_dir = os.getcwd()

	# change to workflow directory
	os.chdir(work_dir)

	# initialize log file
	log_file = ".workflow.log"
	with open(log_file, "w") as f:
		f.write("")

	# launch workflow, wait for completion
	if NEXTFLOW_K8S:
		args = [
			"nextflow",
			"-config", "nextflow.config",
			"kuberun",
			pipeline,
			"-ansi-log", "false",
			"-latest",
			"-profile", profiles,
			"-revision", revision,
			"-volume-mount", PVC_NAME
		]
	else:
		args = [
			"nextflow",
			"-config", "nextflow.config",
			"run",
			pipeline,
			"-ansi-log", "false",
			"-latest",
			"-profile", profiles,
			"-revision", revision,
			"-with-docker"
		]

	if resume:
		args.append("-resume")

	rc = run_cmd(args, log_file)

	# return to original directory
	os.chdir(prev_dir)

	return rc



def save_output(id, output_dir):
	return run_cmd(["./save-output.sh", id, output_dir])



if __name__ == "__main__":
	# parse command-line arguments
	parser = argparse.ArgumentParser(description="Script for running Nextflow workflow")
	parser.add_argument("--id", help="Workflow instance ID", required=True)
	parser.add_argument("--output-dir", help="Output directory", default="output")
	parser.add_argument("--pipeline", help="Name of nextflow pipeline", required=True)
	parser.add_argument("--profiles", help="Comma-separated list of configuration profiles", default="standard")
	parser.add_argument("--resume", help="Whether to to a resumed run", action="store_true")
	parser.add_argument("--revision", help="Project revision", default="master")

	args = parser.parse_args()

	# run workflow
	work_dir = "%s/%s" % (WORKFLOWS_DIR, args.id)
	log_file = "%s/.workflow.log" % work_dir

	rc = run_workflow(args.pipeline, args.profiles, args.resume, args.revision, work_dir, log_file)
	if rc != 0:
		save_status(work_dir, "failed")
		sys.exit(rc)

	# save output data
	output_dir = "%s/%s/%s" % (WORKFLOWS_DIR, args.id, args.output_dir)

	rc = save_output(args.id, output_dir)
	if rc != 0:
		save_status(work_dir, "failed")
		sys.exit(rc)

	# save final status
	save_status(work_dir, "completed")
