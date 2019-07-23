#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import tornado
import tornado.escape
import tornado.httpserver
import tornado.web
import uuid



API_VERSION = 0.4
PORT = 8080
NEXTFLOW_K8S = True if os.environ.get("NEXTFLOW_K8S") else False
WORKFLOWS_DIR = "/workspace/_workflows" if NEXTFLOW_K8S else "./_workflows"



CHILD_PROCESSES = {}



def launch_child_process(args):
	proc = subprocess.Popen(args, stdout=sys.stdout.fileno(), stderr=subprocess.STDOUT)
	CHILD_PROCESSES[proc.pid] = proc
	return proc



def is_process_running(pid_file):
	# read pid from file
	f = open(pid_file)
	pid = int(f.readline().strip())

	# retrieve process from child process list
	try:
		proc = CHILD_PROCESSES[pid]

	# return false if process does not exist
	except KeyError:
		return False

	# determine whether process finished
	return proc.poll() == None



def message(status, message):
	return {
		"status": status,
		"message": message
	}



class GetVersionHandler(tornado.web.RequestHandler):
	def get(self):
		self.set_status(200)
		self.write({
			"version": API_VERSION
		})



class WorkflowQueryHandler(tornado.web.RequestHandler):

	def get(self):
		# get workflow ids
		workflow_ids = os.listdir(WORKFLOWS_DIR)
		workflow_ids = [id for id in workflow_ids if os.path.isdir("%s/%s" % (WORKFLOWS_DIR, id))]

		# get workflow objects
		workflows = [json.load(open("%s/%s/config.json" % (WORKFLOWS_DIR, id))) for id in workflow_ids]

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflows))



class WorkflowCreateHandler(tornado.web.RequestHandler):

	REQUIRED_KEYS = set([
		"pipeline"
	])

	DEFAULTS = {
		"name": "",
		"revision": "master",
		"input_dir": "input",
		"output_dir": "output"
	}

	def get(self):
		workflow = {**self.DEFAULTS, **{ "id": "0" }}

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflow))

	def post(self):
		try:
			# make sure request body is valid
			data = tornado.escape.json_decode(self.request.body)
			missing_keys = self.REQUIRED_KEYS - data.keys()

			if missing_keys:
				self.set_status(400)
				self.write(message(400, "Missing required field(s): %s" % list(missing_keys)))
				return

			# create workflow directory
			id = uuid.uuid4().hex
			work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

			os.makedirs(work_dir)

			# create workflow
			workflow = {**self.DEFAULTS, **data, **{ "id": id, "status": "nascent" }}

			# append creation timestamp to workflow
			workflow["date_created"] = int(time.time() * 1000)

			# save workflow
			json.dump(workflow, open("%s/config.json" % work_dir, "w"))

			self.set_status(200)
			self.set_header("Content-type", "application/json")
			self.write(tornado.escape.json_encode({ "id": id }))
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))



class WorkflowEditHandler(tornado.web.RequestHandler):

	REQUIRED_KEYS = set([
		"pipeline"
	])

	DEFAULTS = {
		"name": "",
		"revision": "master",
		"input_dir": "input",
		"output_dir": "output"
	}

	def get(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# load workflow data from config.json
		workflow = json.load(open("%s/config.json" % work_dir, "r"))

		# append list of input files
		input_dir = "%s/%s" % (work_dir, workflow["input_dir"])

		if os.path.exists(input_dir):
			workflow["input_data"] = os.listdir(input_dir)
		else:
			workflow["input_data"] = []

		# append status of output data
		workflow["output_data"] = os.path.exists("%s/%s-output.tar.gz" % (work_dir, id))

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflow))

	def post(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		try:
			# make sure request body is valid
			data = tornado.escape.json_decode(self.request.body)
			missing_keys = self.REQUIRED_KEYS - data.keys()

			if missing_keys:
				self.set_status(400)
				self.write(message(400, "Missing required field(s): %s" % list(missing_keys)))
				return

			# save workflow config
			config_file = "%s/config.json" % work_dir
			workflow = json.load(open(config_file))

			workflow = {**self.DEFAULTS, **workflow, **data}

			json.dump(workflow, open(config_file, "w"))

			self.set_status(200)
			self.set_header("Content-type", "application/json")
			self.write(tornado.escape.json_encode({ "id": id }))
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))

	def delete(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# delete workflow directory
		shutil.rmtree(work_dir)

		self.set_status(200)
		self.write(message(200, "Workflow \"%s\" has been deleted" % id))



class WorkflowUploadHandler(tornado.web.RequestHandler):

	def post(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# make sure request body contains files
		files = self.request.files

		if not files:
			self.set_status(400)
			self.write(message(400, "No files were uploaded"))
			return

		# load workflow data from config.json
		workflow = json.load(open("%s/config.json" % work_dir, "r"))

		# initialize input directory
		input_dir = "%s/%s" % (work_dir, workflow["input_dir"])
		os.makedirs(input_dir, exist_ok=True)

		# save uploaded files to input directory
		filenames = []

		for f_list in files.values():
			for f_arg in f_list:
				filename, body = f_arg["filename"], f_arg["body"]
				with open("%s/%s" % (input_dir, filename), "wb") as f:
					f.write(body)
				filenames.append(filename)

		self.set_status(200)
		self.write(message(200, "File %s has been uploaded for workflow \"%s\" successfully" % (filenames, id)))



class WorkflowLaunchHandler(tornado.web.RequestHandler):

	resume = False

	def post(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# load workflow data from config.json
		workflow = json.load(open("%s/config.json" % work_dir, "r"))

		# copy nextflow.config from input directory if it exists
		input_dir = "%s/%s" % (work_dir, workflow["input_dir"])
		src = "%s/%s" % (input_dir, "nextflow.config")
		dst = "%s/%s" % (work_dir, "nextflow.config")

		if os.path.exists(src):
			shutil.copyfile(src, dst)
		elif os.path.exists(dst):
			os.remove(dst)

		# append additional settings to nextflow.config
		with open(dst, "a") as f:
			f.write("k8s { launchDir = \"%s\" }" % (work_dir))

		# initialize pid file
		pid_file = "%s/.workflow.pid" % work_dir

		if os.path.exists(pid_file):
			if is_process_running(pid_file):
				self.set_status(400)
				self.write(message(400, "Workflow \"%s\" is already running" % id))
				return
			os.remove(pid_file)

		# launch workflow as a child process
		args = [
			"./workflow.py",
			"--id", id,
			"--pipeline", workflow["pipeline"],
			"--revision", workflow["revision"],
			"--output-dir", workflow["output_dir"]
		]

		if self.resume:
			args.append("--resume")

		proc = launch_child_process(args)

		# save child process id to file
		with open(pid_file, "w") as f:
			f.write(str(proc.pid))

		# update workflow status
		workflow["status"] = "running"

		json.dump(workflow, open("%s/config.json" % work_dir, "w"))

		self.set_status(200)
		self.write(message(200, "Workflow \"%s\" has been launched" % id))



class WorkflowResumeHandler(WorkflowLaunchHandler):

	resume = True



class WorkflowLogHandler(tornado.web.RequestHandler):

	def get(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# load workflow data from config.json
		workflow = json.load(open("%s/config.json" % work_dir, "r"))

		# append log if it exists
		log_file = "%s/.workflow.log" % work_dir

		if os.path.exists(log_file):
			f = open(log_file)
			log = "".join(f.readlines())
		else:
			log = ""

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode({ "id": id, "status": workflow["status"], "log": log }))



class WorkflowDownloadHandler(tornado.web.StaticFileHandler):

	def parse_url_path(self, id):
		self.set_header("Content-Disposition", "attachment; filename=\"%s-output.tar.gz\"" % id)
		return os.path.join(id, "%s-output.tar.gz" % id)



if __name__ == "__main__":
	# initialize workflow directory
	os.makedirs(WORKFLOWS_DIR, exist_ok=True)

	# initialize server
	app = tornado.web.Application([
		(r"/api/version", GetVersionHandler),
		(r"/api/workflows", WorkflowQueryHandler),
		(r"/api/workflows/0", WorkflowCreateHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)", WorkflowEditHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/upload", WorkflowUploadHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/launch", WorkflowLaunchHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/resume", WorkflowResumeHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/log", WorkflowLogHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/download", WorkflowDownloadHandler, dict(path=WORKFLOWS_DIR)),
		(r"/(.*)", tornado.web.StaticFileHandler, dict(path="./client", default_filename="index.html"))
	])

	server = tornado.httpserver.HTTPServer(app)
	server.bind(PORT)
	server.start()

	print("The API is listening on http://0.0.0.0:%d" % PORT, flush=True)
	tornado.ioloop.IOLoop.instance().start()
