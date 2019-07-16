#! /usr/bin/env python3

import os
import json
import uuid
import shlex
import shutil
import psutil
import getpass
import tornado

from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE

from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado.httpserver import HTTPServer
from tornado.escape import json_encode, json_decode

VERSION = 0.2

PORT = 8080
WORK_DIR = '/workspace/_workflows'
NEXTFLOW_CONFIG_FN = 'nextflow.config'

NOT_EXIST = 'Workflow "%s" does not exist'
NOT_READY = 'Workflow "%s" is not ready to launch, reason: %s'


def init():
  os.makedirs(WORK_DIR, exist_ok=True)


def get_process(pid_f):
  with open(pid_f) as f:
    try:
      pid = int(f.readline().strip())
      return psutil.Process(pid)
    except psutil.NoSuchProcess:
      return None


def message(code, msg):
  return {
    'status': code,
    'message': msg
  }


class WorkflowHandler(RequestHandler):

  REQUIRED = set([
    'image'
  ])

  def get(self):
    self.set_status(200)
    self.set_header('Content-type', 'application/json')
    self.write(json_encode(os.listdir(WORK_DIR)))

  def post(self):
    try:
      data = json_decode(self.request.body)
      missing = self.REQUIRED - data.keys()
      if missing:
        self.set_status(400)
        self.write(message(400, 'Missing required field(s): %s\n'%list(missing)))
        return
      wfid = uuid.uuid4().hex
      work_dir = '%s/%s'%(WORK_DIR, wfid)
      # create workspace
      os.makedirs(work_dir)
      # persist workflow config
      with open('%s/config.json'%work_dir, 'w') as f:
        json.dump(data, f)
      self.set_status(201)
      self.write({
        'uuid': wfid,
      })
    except json.JSONDecodeError:
      self.set_status(422)
      self.write(message(422, 'Ill-formatted JSON'))


class WorkflowDeleteHandler(RequestHandler):

  def delete(self, wfid):
    work_dir = '%s/%s'%(WORK_DIR, wfid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST%wfid))
      return
    shutil.rmtree(work_dir)
    self.set_status(200)
    self.write(message(200, 'Workflow "%s" has been deleted'%wfid))


class WorkflowUploadHandler(RequestHandler):

  def post(self, wfid):
    work_dir = '%s/%s'%(WORK_DIR, wfid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST%wfid))
      return
    files = self.request.files
    if not files:
      self.set_status(400)
      self.write(message(400, 'No file is uploaded'))
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
    self.write(message(200, 'File %s has been uploaded for workflow "%s" successfully'%(uploaded, wfid)))


class WorkflowLaunchHandler(RequestHandler):

  def post(self, wfid):
    # make sure workflow directory exists
    work_dir = '%s/%s'%(WORK_DIR, wfid)

    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST%wfid))
      return

    # stage nextflow.config if it exists
    input_dir = '%s/input'%work_dir

    if os.path.exists(input_dir):
      src = '%s/%s'%(input_dir, NEXTFLOW_CONFIG_FN)
      dst = '%s/%s'%(work_dir, NEXTFLOW_CONFIG_FN)
      if os.path.exists(src):
        shutil.copyfile(src, dst)
      with open(dst, 'a') as f:
        f.write('k8s { launchDir = "%s" }'%(work_dir))

    # clear up status files
    pid_f, status_f = '%s/.pid'%work_dir, '%s/.status'%work_dir
    if os.path.exists(pid_f):
      if get_process(pid_f):
        self.set_status(400)
        self.write(message(400, 'Workflow "%s" is running now and cannot be re-launched'%wfid))
        return
      os.remove(pid_f)
    if os.path.exists(status_f):
      os.remove(status_f)

    with open('%s/config.json'%work_dir) as f:
      data = json.load(f)
      cmd = './workflow.py --wfid %s --image %s --kube %d'%(wfid, data['image'], args.kube)
      p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
      with open('%s/.pid'%work_dir, 'w') as pid_f:
        pid_f.write(str(p.pid))
    self.set_status(200)
    self.write(message(200, 'Workflow "%s" has been launched\n'%wfid))


class WorkflowLogHandler(RequestHandler):

  def get(self, wfid):
    work_dir = '%s/%s'%(WORK_DIR, wfid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST%wfid))
      return
    with open('%s/log'%work_dir) as f:
      self.set_status(200)
      self.write({
        'log': '<pre>%s</pre>'%''.join(f.readlines()),
      })


class WorkflowStatusHandler(RequestHandler):

  STATUSES = {
    'nascent': 'Workflow "%s" is not yet launched',
    'running': 'Workflow "%s" is running',
    'failed': 'Workflow "%s" failed',
    'completed': 'Workflow "%s" has completed',
  }

  def get(self, wfid):
    work_dir = '%s/%s'%(WORK_DIR, wfid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(message(404, NOT_EXIST%wfid))
      return
    status, msg = 'nascent', None

    pid_f = '%s/.pid'%work_dir
    status_f = '%s/.status'%work_dir
    if os.path.exists(status_f):
      with open(status_f) as f:
        status = json.load(f)
        rc, msg = status['rc'], status['message']
        if rc == 0:
          status = 'completed'
        else:
          status = 'failed'
    elif os.path.exists(pid_f) and get_process(pid_f):
      status = 'running'
    self.set_status(200)
    self.write({
      'status': status,
      'message': msg if msg else self.STATUSES[status]%wfid,
    })

class WorkflowDownloadHandler(StaticFileHandler):

  def parse_url_path(self, wfid):
    self.set_header('Content-Disposition', 'attachment; filename="output-%s.tar.gz"'%wfid)
    return os.path.join(WORK_DIR, wfid, 'output-%s.tar.gz'%wfid)

class GetVersionHandler(RequestHandler):
  def get(self):
    self.set_status(200)
    self.write({
      'version': VERSION
    })

if __name__ == "__main__":
  # parse command-line arguments
  parser = ArgumentParser()
  parser.add_argument('--kube', dest='kube', type=bool, default=False,
                      help='Whether to use kubernetes executor')
  args = parser.parse_args()

  # initialize server
  app = Application([
    (r'/version', GetVersionHandler),
    (r'/workflow', WorkflowHandler),
    (r'/workflow/([a-zA-Z0-9-]+)\/*', WorkflowDeleteHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/upload\/*', WorkflowUploadHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/launch\/*', WorkflowLaunchHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/log\/*', WorkflowLogHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/status\/*', WorkflowStatusHandler),
    (r'/workflow/([a-zA-Z0-9-]+)/download\/*', WorkflowDownloadHandler, dict(path=WORK_DIR)),
  ])
  init()
  server = HTTPServer(app)
  server.bind(PORT)
  server.start()
  print('The API is listening on http://0.0.0.0:%d'%PORT, flush=True)
  tornado.ioloop.IOLoop.instance().start()
