#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import sys



PVC_NAME = os.environ.get("PVC_NAME", "deepgtex-prp")
WORKFLOWS_DIR = "/workspace/_workflows"



os.environ["NXF_VER"] = "19.07.0-edge"



def run_cmd(cmd, log_file=None, debug=True):
  # run command as child process
  p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

  # wait for command to finish
  while True:
    # read line from stdout
    line = p.stdout.readline()

    # break if process is done
    if not line and p.poll() is not None:
      break

    # write line to log file
    if line:
      if log_file:
        with open(log_file, "a") as f:
          f.write(str(line, "utf-8"))
          f.flush()

      if log_file is None or debug:
        sys.stdout.write("%d: %s" % (p.pid, line.decode("ascii", "ignore")))
        sys.stdout.flush()

  return p.returncode



def save_status(work_dir, status):
  data = json.load(open("%s/config.json" % work_dir))
  data["status"] = status

  json.dump(data, open("%s/config.json" % work_dir, "w"))



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



def save_output(id):
  return run_cmd("./save-output.sh %s %s/%s/output" % (id, WORKFLOWS_DIR, id))



if __name__ == "__main__":
  # parse command-line arguments
  parser = argparse.ArgumentParser(description="Script for running Nextflow workflow")
  parser.add_argument("--id", required=True, help="Workflow instance ID")
  parser.add_argument("--pipeline", required=True, help="Name of nextflow pipeline")
  parser.add_argument("--kube", action="store_true", help="Whether to use kubernetes executor")

  args = parser.parse_args()

  # run workflow
  work_dir = "%s/%s" % (WORKFLOWS_DIR, args.id)
  log_file = "%s/.workflow.log" % work_dir

  save_status(work_dir, "running")

  rc = run_workflow(args.pipeline, work_dir, log_file, kube=args.kube)
  if rc != 0:
    save_status(work_dir, "failed")
    sys.exit(rc)

  # save output data
  rc = save_output(args.id)
  if rc != 0:
    save_status(work_dir, "failed")
    sys.exit(rc)

  # save final status
  save_status(work_dir, "completed")
