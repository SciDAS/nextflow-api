#! /usr/bin/env python3 

import os
import json
import shlex 
import shutil
import getpass
import tornado

from pathlib import Path
from subprocess import Popen, PIPE

from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado.httpserver import HTTPServer
from tornado.escape import json_encode, json_decode


PORT = 8080
WORK_DIR = '%s/work_dir'%Path.home()

NOT_EXIST = 'Workflow "%s" does not exist\n'
NOT_READY = 'Workflow "%s" is not ready to launch, reason: %s\n'


def init():
  os.makedirs(WORK_DIR, exist_ok=True)


class WorkflowCreateHandler(RequestHandler):

  REQUIRED = set([
    'uuid', 'image'
  ])

  def post(self):
    try:
      data = json_decode(self.request.body)
      missing = self.REQUIRED - data.keys()
      if missing:
        self.set_status(400)
        self.write('Missing required field(s): %s\n'%list(missing))
        return
      uuid = data['uuid']
      work_dir = '%s/%s'%(WORK_DIR, uuid)
      if os.path.exists(work_dir):
        self.set_status(409)
        self.write('Workflow %s already exists\n'%uuid)
        return
      # create workspace
      os.makedirs(work_dir)
      # persist workflow config
      with open('%s/config.json'%(work_dir), 'w') as f:
        json.dump(data, f)
      self.set_status(201)
      self.write('Workflow "%s" has been created successfully\n'%uuid)
    except json.JSONDecodeError:
      self.set_status(422)
      self.write('Ill-formatted JSON\n')
  

class WorkflowDeleteHandler(RequestHandler):
  
  def delete(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    shutil.rmtree(work_dir)
    self.set_status(200)
    self.write('Workflow "%s" has been deleted\n'%uuid)


class WorkflowUploadHandler(RequestHandler):
  
  def post(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    files = self.request.files
    if not files:
      self.set_status(400)
      self.write('No file is uploaded\n')
      return
    uploaded = []
    for f_list in files.values():
      for f_arg in f_list:
        fn, body = f_arg['filename'], f_arg['body']
        input_dir = '%s/input'%work_dir
        os.makedirs(input_dir, exist_ok=True)
        with open('%s/%s'%(input_dir, fn), 'wb') as f:
          f.write(body)
        uploaded += fn,
    self.set_status(200)
    self.write('File %s has been uploaded for workflow "%s" successfully'%(uploaded, uuid))


class WorkflowLaunchHandler(RequestHandler):

  def post(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    input_dir = '%s/input'%work_dir
    if os.path.exists(input_dir):
      nxt_cfg = [fn for fn in os.listdir(input_dir) if fn.endswith('.config')]
      if not nxt_cfg:
        self.set_status(400)
        self.write(NOT_READY%(uuid, 'Nextflow config is missing'))
        return
      nxt_cfg = nxt_cfg[0]
      src, dst = '%s/%s'%(input_dir, nxt_cfg), '%s/%s'%(work_dir, nxt_cfg)
      shutil.copyfile(src, dst)
      with open(dst, 'a') as f:
        f.write('k8s {\n\tlaunchDir = "/workspace/%s/%s"\n}'%(getpass.getuser(), uuid))
    else:
      self.set_status(400)
      self.write(NOT_READY%(uuid, 'Input data is missing'))
      return
    with open('%s/config.json'%work_dir) as f:
      data = json.load(f)
      cmd = './run-workflow.py --uuid %s --image %s'%(uuid, data['image'])
      Popen(shlex.split(cmd))
    self.set_status(200)
    self.write('Workflow "%s" has been launched\n'%uuid)


class WorkflowLogHandler(RequestHandler):

  def get(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    with open('%s/log'%work_dir) as f:
      self.set_status(200)
      self.write('<pre>%s</pre>'%''.join(f.readlines()))

class WorkflowDownloadHandler(StaticFileHandler):

  def parse_url_path(self, uuid):
    self.set_header('Content-Disposition', 'attachment; filename="output-%s.tar.gz"'%uuid)
    return os.path.join(WORK_DIR, uuid, 'output-%s.tar.gz'%uuid)


if __name__ == "__main__":
  app = Application([
    (r'/workflow', WorkflowCreateHandler), 
    (r'/workflow/([a-zA-Z0-9-]+)\/*', WorkflowDeleteHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/upload\/*', WorkflowUploadHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/launch\/*', WorkflowLaunchHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/log\/*', WorkflowLogHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/download\/*', WorkflowDownloadHandler, dict(path=WORK_DIR)),
  ])
  init()
  server = HTTPServer(app)
  server.bind(PORT)
  server.start()
  print('The API is listening on http://0.0.0.0:%d'%PORT, flush=True)
  tornado.ioloop.IOLoop.instance().start()
