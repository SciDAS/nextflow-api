#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import sys



PVC_NAME = os.environ.get("PVC_NAME", "deepgtex-prp")
WORKFLOWS_DIR = "/workspace/_workflows"



os.environ["NXF_VER"] = "19.04.0-edge"



def run_cmd(cmd, log_file=None):
  p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=sys.stdout.fileno())
  while True:
    out = p.stdout.readline()
    if not out and p.poll() is not None:
      break
    if out:
      out = str(out, "utf-8")
      if log_file:
        with open(log_file, "a") as f:
          f.write(out)
          f.flush()
      else:
        sys.stdout.write(out)
        sys.stdout.flush()
  return p.returncode



def save_status(work_dir, rc, msg):
  with open("%s/.workflow.status" % work_dir, "w") as f:
    json.dump(dict(rc=rc, message=msg), f)



def run_workflow(pipeline, work_dir, log_file, kube=False):
  # save current directory
  prev_dir = os.getcwd()

  # change to workflow directory
  os.chdir(work_dir)

  # initialize log file
  log_file = ".workflow.log"
  with open(log_file, "w") as f:
    f.write("")

  # launch workflow, wait for completion
  if kube:
    rc = run_cmd("nextflow kuberun -v %s %s" % (PVC_NAME, pipeline), log_file)
  else:
    rc = run_cmd("nextflow run %s -with-docker" % (pipeline), log_file)

  # return to original directory
  os.chdir(prev_dir)

  return rc



def save_output(id, log_file):
  return run_cmd("./save-output.sh %s %s/%s/output" % (id, WORKFLOWS_DIR, id), log_file)



if __name__ == "__main__":
  # parse command-line arguments
  parser = argparse.ArgumentParser(description="Script for running Nextflow workflow")
  parser.add_argument("--id", required=True, help="Workflow instance ID")
  parser.add_argument("--pipeline", required=True, help="Name of nextflow pipeline")
  parser.add_argument("--kube", type=bool, default=False, help="Whether to use kubernetes executor")

  args = parser.parse_args()

  # run workflow
  work_dir = "%s/%s" % (WORKFLOWS_DIR, args.id)
  log_file = "%s/.workflow.log" % work_dir

  rc = run_workflow(args.pipeline, work_dir, log_file, kube=args.kube)
  if rc != 0:
    save_status(work_dir, rc, "Workflow failed")
    sys.exit(rc)

  # save output data
  rc = save_output(args.id, log_file)
  if rc != 0:
    save_status(work_dir, rc, "Failed to save output data")
    sys.exit(rc)

  # save final status
  save_status(work_dir, 0, "Workflow completed")
