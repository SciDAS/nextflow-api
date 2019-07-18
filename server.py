#!/usr/bin/env python3

import argparse
import json
import os
import psutil
import shutil
import subprocess
import sys
import tornado
import uuid

import tornado.escape
import tornado.httpserver
import tornado.web



API_VERSION = 0.4
PORT = 8080
NEXTFLOW_K8S = True if os.environ.get("NEXTFLOW_K8S") else False
WORKFLOWS_DIR = "/workspace/_workflows" if NEXTFLOW_K8S else "./_workflows"



def get_process(pid_file):
	with open(pid_file) as f:
		try:
			pid = int(f.readline().strip())
			return psutil.Process(pid)
		except psutil.NoSuchProcess:
			return None



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
		"pipeline",
		"input_dir",
		"output_dir"
	])

	def get(self):
		workflow = {
			"id": "0",
			"input_dir": "input",
			"output_dir": "output"
		}

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

			# create workflow config
			data["id"] = id
			data["status"] = "nascent"

			json.dump(data, open("%s/config.json" % work_dir, "w"))

			self.set_status(200)
			self.set_header("Content-type", "application/json")
			self.write(tornado.escape.json_encode({ "id": id }))
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))



class WorkflowEditHandler(tornado.web.RequestHandler):

	REQUIRED_KEYS = set([
		"pipeline",
		"input_dir",
		"output_dir"
	])

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

		# append log if it exists
		log_file = "%s/.workflow.log" % work_dir

		if os.path.exists(log_file):
			f = open(log_file)
			workflow["log"] = "".join(f.readlines())

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

			for key in self.REQUIRED_KEYS:
				workflow[key] = data[key]

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

	def post(self, id):
		# make sure workflow directory exists
		work_dir = "%s/%s" % (WORKFLOWS_DIR, id)

		if not os.path.exists(work_dir):
			self.set_status(404)
			self.write(message(404, "Workflow \"%s\" does not exist" % id))
			return

		# load workflow data from config.json
		workflow = json.load(open("%s/config.json" % work_dir, "r"))

		# stage nextflow.config if it exists
		input_dir = "%s/%s" % (work_dir, workflow["input_dir"])

		if os.path.exists(input_dir):
			# copy nextflow.config from input directory to work directory
			src = "%s/%s" % (input_dir, "nextflow.config")
			dst = "%s/%s" % (work_dir, "nextflow.config")
			if os.path.exists(dst):
				os.remove(dst)
			if os.path.exists(src):
				shutil.copyfile(src, dst)

			# append additional settings to nextflow.config
			with open(dst, "a") as f:
				f.write("k8s { launchDir = \"%s\" }" % (work_dir))

		# initialize pid file
		pid_file = "%s/.workflow.pid" % work_dir

		if os.path.exists(pid_file):
			if get_process(pid_file):
				self.set_status(400)
				self.write(message(400, "Workflow \"%s\" is already running" % id))
				return
			os.remove(pid_file)

		# launch workflow as a child process
		args = [
			"./workflow.py",
			"--id", id,
			"--pipeline", workflow["pipeline"],
			"--output-dir", workflow["output_dir"]
		]
		proc = subprocess.Popen(args, stdout=sys.stdout.fileno(), stderr=subprocess.STDOUT)

		with open("%s/.workflow.pid" % work_dir, "w") as pid_file:
			pid_file.write(str(proc.pid))

		self.set_status(200)
		self.write(message(200, "Workflow \"%s\" has been launched" % id))



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
		(r"/api/workflows/([a-zA-Z0-9-]+)/download", WorkflowDownloadHandler, dict(path=WORKFLOWS_DIR)),
		(r"/(.*)", tornado.web.StaticFileHandler, dict(path="./client", default_filename="index.html"))
	])

	server = tornado.httpserver.HTTPServer(app)
	server.bind(PORT)
	server.start()

	print("The API is listening on http://0.0.0.0:%d" % PORT, flush=True)
	tornado.ioloop.IOLoop.instance().start()
