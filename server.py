#! /usr/bin/env python3

import argparse
import json
import os
import psutil
import shlex
import shutil
import subprocess
import tornado
import uuid

import tornado.escape
import tornado.httpserver
import tornado.web



VERSION = 0.2
PORT = 8080
WORKFLOWS_DIR = "/workspace/_workflows"
NEXTFLOW_CONFIG = "nextflow.config"

NOT_EXIST = "Workflow \"%s\" does not exist"



def get_process(pid_file):
  with open(pid_file) as f:
    try:
      pid = int(f.readline().strip())
      return psutil.Process(pid)
    except psutil.NoSuchProcess:
      return None



def message(code, msg):
  return {
    "status": code,
    "message": msg
  }



class GetVersionHandler(tornado.web.RequestHandler):
  def get(self):
    self.set_status(200)
    self.write({
      "version": VERSION
    })



class WorkflowHandler(tornado.web.RequestHandler):

  REQUIRED = set([
    "pipeline"
  ])

  def get(self):
    self.set_status(200)
    self.set_header("Content-type", "application/json")
    self.write(tornado.escape.json_encode(os.listdir(WORKFLOWS_DIR)))

  def post(self):
    try:
      data = tornado.escape.json_decode(self.request.body)
      missing = self.REQUIRED - data.keys()
      if missing:
        self.set_status(400)
        self.write(message(400, "Missing required field(s): %s" % list(missing)))
        return
      id = uuid.uuid4().hex
      work_dir = "%s/%s" % (WORKFLOWS_DIR, id)
      # create workspace
      os.makedirs(work_dir)
      # persist workflow config
      with open("%s/config.json" % work_dir, "w") as f:
        json.dump(data, f)
      self.set_status(201)
      self.write({
        "id": id,
      })
    except json.JSONDecodeError:
      self.set_status(422)
      self.write(message(422, "Ill-formatted JSON"))



class WorkflowDeleteHandler(tornado.web.RequestHandler):

  def delete(self, id):
    work_dir = "%s/%s" % (WORKFLOWS_DIR, id)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST % id))
      return
    shutil.rmtree(work_dir)
    self.set_status(200)
    self.write(message(200, "Workflow \"%s\" has been deleted" % id))



class WorkflowUploadHandler(tornado.web.RequestHandler):

  def post(self, id):
    work_dir = "%s/%s" % (WORKFLOWS_DIR, id)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST % id))
      return
    files = self.request.files
    if not files:
      self.set_status(400)
      self.write(message(400, "No file is uploaded"))
      return
    uploaded = []
    for f_list in files.values():
      for f_arg in f_list:
        fn, body = f_arg["filename"], f_arg["body"]
        input_dir = "%s/input" % work_dir
        os.makedirs(input_dir, exist_ok=True)
        with open("%s/%s" % (input_dir, fn), "wb") as f:
          f.write(body)
        uploaded += fn,
    self.set_status(200)
    self.write(message(200, "File %s has been uploaded for workflow \"%s\" successfully" % (uploaded, id)))



class WorkflowLaunchHandler(tornado.web.RequestHandler):

  def post(self, id):
    # make sure workflow directory exists
    work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST % id))
      return

    # stage nextflow.config if it exists
    input_dir = "%s/input" % work_dir

    if os.path.exists(input_dir):
      src = "%s/%s" % (input_dir, NEXTFLOW_CONFIG)
      dst = "%s/%s" % (work_dir, NEXTFLOW_CONFIG)
      if os.path.exists(src):
        shutil.copyfile(src, dst)
      with open(dst, "a") as f:
        f.write("k8s { launchDir = \"%s\" }" % (work_dir))

    # clear up status files
    pid_file, status_file = "%s/.workflow.pid" % work_dir, "%s/.workflow.status" % work_dir
    if os.path.exists(pid_file):
      if get_process(pid_file):
        self.set_status(400)
        self.write(message(400, "Workflow \"%s\" is running now and cannot be re-launched" % id))
        return
      os.remove(pid_file)
    if os.path.exists(status_file):
      os.remove(status_file)

    with open("%s/config.json" % work_dir) as f:
      data = json.load(f)
      cmd = "./workflow.py --id %s --pipeline %s --kube %d" % (id, data["pipeline"], args.kube)
      p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      with open("%s/.workflow.pid" % work_dir, "w") as pid_file:
        pid_file.write(str(p.workflow.pid))
    self.set_status(200)
    self.write(message(200, "Workflow \"%s\" has been launched" % id))



class WorkflowStatusHandler(tornado.web.RequestHandler):

  STATUSES = {
    "nascent": "Workflow \"%s\" is not yet launched",
    "running": "Workflow \"%s\" is running",
    "failed": "Workflow \"%s\" failed",
    "completed": "Workflow \"%s\" has completed",
  }

  def get(self, id):
    work_dir = "%s/%s" % (WORKFLOWS_DIR, id)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST % id))
      return
    status, msg = "nascent", None

    pid_file = "%s/.workflow.pid" % work_dir
    status_file = "%s/.workflow.status" % work_dir
    if os.path.exists(status_file):
      with open(status_file) as f:
        status = json.load(f)
        rc, msg = status["rc"], status["message"]
        if rc == 0:
          status = "completed"
        else:
          status = "failed"
    elif os.path.exists(pid_file) and get_process(pid_file):
      status = "running"
    self.set_status(200)
    self.write({
      "status": status,
      "message": msg if msg else self.STATUSES[status]%id,
    })



class WorkflowLogHandler(tornado.web.RequestHandler):

  def get(self, id):
    work_dir = "%s/%s" % (WORKFLOWS_DIR, id)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST % id))
      return
    with open("%s/.workflow.log" % work_dir) as f:
      self.set_status(200)
      self.write({
        "log": "".join(f.readlines()),
      })



class WorkflowDownloadHandler(tornado.web.StaticFileHandler):

  def parse_url_path(self, id):
    self.set_header("Content-Disposition", "attachment; filename=\"output-%s.tar.gz\"" % id)
    return os.path.join(WORKFLOWS_DIR, id, "output-%s.tar.gz" % id)



if __name__ == "__main__":
  # parse command-line arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("--kube", type=bool, default=False, help="Whether to use kubernetes executor")

  args = parser.parse_args()

  # initialize workflow directory
  os.makedirs(WORKFLOWS_DIR, exist_ok=True)

  # initialize server
  app = tornado.web.Application([
    (r"/version", GetVersionHandler),
    (r"/workflow", WorkflowHandler),
    (r"/workflow/([a-zA-Z0-9-]+)\/*", WorkflowDeleteHandler),
    (r"/workflow/([a-zA-Z0-9-]+)/upload\/*", WorkflowUploadHandler),
    (r"/workflow/([a-zA-Z0-9-]+)/launch\/*", WorkflowLaunchHandler),
    (r"/workflow/([a-zA-Z0-9-]+)/status\/*", WorkflowStatusHandler),
    (r"/workflow/([a-zA-Z0-9-]+)/log\/*", WorkflowLogHandler),
    (r"/workflow/([a-zA-Z0-9-]+)/download\/*", WorkflowDownloadHandler, dict(path=WORKFLOWS_DIR)),
  ])
  server = tornado.httpserver.HTTPServer(app)
  server.bind(PORT)
  server.start()

  print("The API is listening on http://0.0.0.0:%d" % PORT, flush=True)
  tornado.ioloop.IOLoop.instance().start()
