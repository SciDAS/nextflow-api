#! /usr/bin/env python3 

import os
import json
import shlex 
import shutil
import psutil
import getpass
import tornado

from pathlib import Path
from subprocess import Popen, PIPE

from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado.httpserver import HTTPServer
from tornado.escape import json_encode, json_decode


PORT = 8080
WORK_DIR = '%s/work_dir'%Path.home()
NEXTFLOW_CONFIG_FN = 'nextflow.config'

NOT_EXIST = 'Workflow "%s" does not exist\n'
NOT_READY = 'Workflow "%s" is not ready to launch, reason: %s\n'


def init():
  os.makedirs(WORK_DIR, exist_ok=True)


def get_process(pid_f):
  with open(pid_f) as f:
    try:
      pid = int(f.readline().strip())
      return psutil.Process(pid)
    except psutil.NoSuchProcess:
      return None


class WorkflowHandler(RequestHandler):

  REQUIRED = set([
    'uuid', 'image'
  ])

  def get(self):
    self.set_status(200)
    self.write(json_encode(os.listdir(WORK_DIR)) + '\n')

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
  
  def initialize(self, nfs_pod):
    self.__nfs_pod = nfs_pod

  def delete(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    shutil.rmtree(work_dir)
    if self.__nfs_pod:
      self._delete_on_nfs(uuid)
    self.set_status(200)
    self.write('Workflow "%s" has been deleted\n'%uuid)
  
  def _delete_on_nfs(self, uuid):
    cmd = 'kubectl exec %s -- bash -c "rm -rf /exports/dc/%s"'%(self.__nfs_pod, uuid)
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    p.wait(timeout=3)


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
    self.write('File %s has been uploaded for workflow "%s" successfully\n'%(uploaded, uuid))


class WorkflowLaunchHandler(RequestHandler):

  def post(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
      return 
    input_dir = '%s/input'%work_dir
    if os.path.exists(input_dir):
      if not os.path.exists('%s/%s'%(input_dir, NEXTFLOW_CONFIG_FN)):
        self.set_status(400)
        self.write(NOT_READY%(uuid, 'Nextflow config is missing'))
        return
      src, dst = '%s/%s'%(input_dir, NEXTFLOW_CONFIG_FN), '%s/%s'%(work_dir, NEXTFLOW_CONFIG_FN)
      shutil.copyfile(src, dst)
      with open(dst, 'a') as f:
        f.write('k8s {\n\tlaunchDir = "/workspace/%s/%s"\n}'%(getpass.getuser(), uuid))
    else:
      self.set_status(400)
      self.write(NOT_READY%(uuid, 'Input data is missing'))
      return

    # clear up status files
    pid_f, status_f = '%s/.pid'%work_dir, '%s/.status'%work_dir
    if os.path.exists(pid_f):
      if get_process(pid_f):
        self.set_status(400)
        self.write('Workflow "%s" is running now and cannot be re-launched\n'%uuid)
        return
      os.remove(pid_f)
    if os.path.exists(status_f):
      os.remove(status_f)

    with open('%s/config.json'%work_dir) as f:
      data = json.load(f)
      cmd = './run-workflow.py --uuid %s --image %s'%(uuid, data['image'])
      p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
      with open('%s/.pid'%work_dir, 'w') as pid_f:
        pid_f.write(str(p.pid))
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


class WorkflowStatusHandler(RequestHandler):

  STATUSES = {
    'nascent': 'Workflow "%s" is not yet launched',
    'running': 'Workflow "%s" is running',
    'failed': 'Workflow "%s" failed',
    'completed': 'Workflow "%s" has completed',
  }

  def get(self, uuid):
    work_dir = '%s/%s'%(WORK_DIR, uuid)
    if not os.path.exists(work_dir):
      self.set_status(404)
      self.write(NOT_EXIST%uuid)
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
    self.write('status: %s\nmessage: %s\n'%(status, msg if msg else self.STATUSES[status]%uuid))


class WorkflowDownloadHandler(StaticFileHandler):

  def parse_url_path(self, uuid):
    self.set_header('Content-Disposition', 'attachment; filename="output-%s.tar.gz"'%uuid)
    return os.path.join(WORK_DIR, uuid, 'output-%s.tar.gz'%uuid)


def get_nfs_pod():
  out, _ = Popen(shlex.split('kubectl get pods'), stdout=PIPE, stderr=PIPE).communicate()
  if out:
    for l in str(out, 'utf-8').split('\n'):
      if 'nfs-server' not in l:
        continue
      return l.split()[0]
  return None


if __name__ == "__main__":
  nfs_pod = get_nfs_pod()
  app = Application([
    (r'/workflow', WorkflowHandler), 
    (r'/workflow/([a-zA-Z0-9-]+)\/*', WorkflowDeleteHandler, dict(nfs_pod=nfs_pod)),
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
