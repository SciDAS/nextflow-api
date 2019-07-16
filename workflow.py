#!/usr/bin/env python3

import os
import sys
import json
import shlex

from argparse import ArgumentParser
from subprocess import Popen, PIPE
from pathlib import Path


VOL_NAME = os.environ.get('VOL_NAME', 'deepgtex-prp')
WORK_DIR = '/workspace/_workflows'


os.environ['NXF_VER'] = '19.04.0-edge'


def parse_args():
  parser = ArgumentParser(description='Script for running Nextflow workflow')
  parser.add_argument('--uuid', dest='uuid', type=str, required=True,
                      help='UUID of the workflow run')
  parser.add_argument('--image', dest='image', type=str, required=True,
                      help='Container image of the workflow')
  parser.add_argument('--kube', dest='kube', type=bool, default=False,
                      help='Whether to use kubernetes executor')
  return parser.parse_args()


def run_cmd(cmd, log_file=None):
  p = Popen(shlex.split(cmd), stdout=PIPE, stderr=sys.stdout.fileno())
  while True:
    out = p.stdout.readline()
    if not out and p.poll() is not None:
      break
    if out:
      out = str(out, 'utf-8')
      if log_file:
        with open(log_file, 'a') as f:
          f.write(out)
          f.flush()
      else:
        sys.stdout.write(out)
        sys.stdout.flush()
  return p.returncode


def save_status(work_dir, rc, msg):
  with open('%s/.status'%work_dir, 'w') as f:
    json.dump(dict(rc=rc, message=msg), f)


def clear_log(work_dir):
  log_f = '%s/log'%work_dir
  if os.path.exists(log_f):
    os.remove(log_f)


def load_data(uuid, log_file):
  return run_cmd('kube-load.sh %s %s/%s/input'%(VOL_NAME, WORK_DIR, uuid), log_file)


def run_workflow(image, work_dir, log_file, kube=False):
  os.chdir(work_dir)
  if kube:
    return run_cmd('nextflow kuberun -v %s %s'%(VOL_NAME, image), log_file)
  else:
    return run_cmd('nextflow run %s -with-docker'%(image), log_file)


def save_data(uuid, log_file):
  return run_cmd('kube-save.sh %s %s/%s'%(VOL_NAME, WORK_DIR, uuid), log_file)


if __name__ == "__main__":
  args = parse_args()
  uuid = args.uuid
  work_dir = '%s/%s'%(WORK_DIR, uuid)
  log_f = '%s/log'%work_dir
  clear_log(work_dir)
  rc = run_workflow(args.image, work_dir, log_f, kube=args.kube)
  if rc != 0:
    save_status(work_dir, rc, 'Workflow failed')
    sys.exit(rc)
  save_status(work_dir, 0, 'Workflow completed')
