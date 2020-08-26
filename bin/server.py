#!/usr/bin/env python3

import argparse
import bson
import json
import multiprocessing as mp
import os
import shutil
import signal
import socket
import time
import tornado
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import backend
import env
import workflow as Workflow



def list_dir_recursive(path, relpath_start=""):
	files = [os.path.join(dir, f) for (dir, subdirs, filenames) in os.walk(path) for f in filenames]
	files = [os.path.relpath(f, start=relpath_start) for f in files]
	files.sort()

	return files



def message(status, message):
	return {
		"status": status,
		"message": message
	}



class WorkflowQueryHandler(tornado.web.RequestHandler):

	async def get(self):
		page = int(self.get_query_argument("page", 0))
		page_size = int(self.get_query_argument("page_size", 100))

		db = self.settings["db"]
		workflows = await db.workflow_query(page, page_size)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflows))



class WorkflowCreateHandler(tornado.web.RequestHandler):

	REQUIRED_KEYS = set([
		"pipeline"
	])

	DEFAULTS = {
		"name": "",
		"profiles": "standard",
		"revision": "master",
		"input_dir": "input",
		"output_dir": "output"
	}

	def get(self):
		workflow = {**self.DEFAULTS, **{ "_id": "0" }}

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflow))

	async def post(self):
		db = self.settings["db"]

		# make sure request body is valid
		try:
			data = tornado.escape.json_decode(self.request.body)
			missing_keys = self.REQUIRED_KEYS - data.keys()
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))
			return

		if missing_keys:
			self.set_status(400)
			self.write(message(400, "Missing required field(s): %s" % list(missing_keys)))
			return

		# create workflow
		workflow = {**self.DEFAULTS, **data, **{ "status": "nascent" }}
		workflow["_id"] = str(bson.ObjectId())

		# append creation timestamp to workflow
		workflow["date_created"] = int(time.time() * 1000)

		# save workflow
		await db.workflow_create(workflow)

		# create workflow directory
		work_dir = os.path.join(env.WORKFLOWS_DIR, workflow["_id"])
		os.makedirs(work_dir)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode({ "_id": workflow["_id"] }))




class WorkflowEditHandler(tornado.web.RequestHandler):

	REQUIRED_KEYS = set([
		"pipeline"
	])

	DEFAULTS = {
		"name": "",
		"profiles": "standard",
		"revision": "master",
		"input_dir": "input",
		"output_dir": "output"
	}

	async def get(self, id):
		db = self.settings["db"]

		# get workflow
		workflow = await db.workflow_get(id)

		# append list of input files
		work_dir = os.path.join(env.WORKFLOWS_DIR, id)
		input_dir = os.path.join(work_dir, workflow["input_dir"])
		output_dir = os.path.join(work_dir, workflow["output_dir"])

		if os.path.exists(input_dir):
			workflow["input_files"] = list_dir_recursive(input_dir, relpath_start=work_dir)
		else:
			workflow["input_files"] = []

		# append list of output files
		if os.path.exists(output_dir):
			workflow["output_files"] = list_dir_recursive(output_dir, relpath_start=work_dir)
		else:
			workflow["output_files"] = []

		# append status of output data
		workflow["output_data"] = os.path.exists("%s/%s-output.tar.gz" % (work_dir, id))

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(workflow))

	async def post(self, id):
		db = self.settings["db"]

		# make sure request body is valid
		try:
			data = tornado.escape.json_decode(self.request.body)
			missing_keys = self.REQUIRED_KEYS - data.keys()
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))

		if missing_keys:
			self.set_status(400)
			self.write(message(400, "Missing required field(s): %s" % list(missing_keys)))
			return

		# save workflow config
		workflow = await db.workflow_get(id)
		workflow = {**self.DEFAULTS, **workflow, **data}

		await db.workflow_update(id, workflow)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode({ "_id": id }))

	async def delete(self, id):
		db = self.settings["db"]

		try:
			# delete workflow
			await db.workflow_delete(id)

			# delete workflow directory
			shutil.rmtree(os.path.join(env.WORKFLOWS_DIR, id), ignore_errors=True)

			self.set_status(200)
			self.write(message(200, "Workflow \"%s\" was deleted" % id))
		except:
			self.set_status(404)
			self.write(message(404, "Failed to delete workflow \"%s\"" % id))




class WorkflowUploadHandler(tornado.web.RequestHandler):

	async def post(self, id):
		db = self.settings["db"]

		# make sure request body contains files
		files = self.request.files

		if not files:
			self.set_status(400)
			self.write(message(400, "No files were uploaded"))
			return

		# get workflow
		workflow = await db.workflow_get(id)

		# initialize input directory
		input_dir = os.path.join(env.WORKFLOWS_DIR, id, workflow["input_dir"])
		os.makedirs(input_dir, exist_ok=True)

		# save uploaded files to input directory
		filenames = []

		for f_list in files.values():
			for f_arg in f_list:
				filename, body = f_arg["filename"], f_arg["body"]
				with open(os.path.join(input_dir, filename), "wb") as f:
					f.write(body)
				filenames.append(filename)

		self.set_status(200)
		self.write(message(200, "File \"%s\" was uploaded for workflow \"%s\" successfully" % (filenames, id)))



class WorkflowLaunchHandler(tornado.web.RequestHandler):

	resume = False

	async def post(self, id):
		db = self.settings["db"]

		# get workflow
		workflow = await db.workflow_get(id)

		# make sure workflow is not already running
		if workflow["status"] == "running":
			self.set_status(400)
			self.write(message(400, "Workflow \"%s\" is already running" % id))
			return

		# copy nextflow.config from input directory if it exists
		work_dir = os.path.join(env.WORKFLOWS_DIR, id)
		input_dir = os.path.join(work_dir, workflow["input_dir"])
		src = os.path.join(input_dir, "nextflow.config")
		dst = os.path.join(work_dir, "nextflow.config")

		if os.path.exists(src):
			shutil.copyfile(src, dst)
		elif os.path.exists(dst):
			os.remove(dst)

		# append additional settings to nextflow.config
		with open(dst, "a") as f:
			f.write("weblog { enabled = true\n url = \"http://%s:8080/api/tasks\" }\n" % (socket.gethostbyname(socket.gethostname())))
			f.write("k8s { launchDir = \"%s\" }\n" % (work_dir))

		try:
			# update workflow status
			workflow["status"] = "running"
			workflow["date_submitted"] = int(time.time() * 1000)

			await db.workflow_update(id, workflow)

			# launch workflow as a child process
			p = mp.Process(target=Workflow.launch, args=(db, workflow, self.resume))
			p.start()

			self.set_status(200)
			self.write(message(200, "Workflow \"%s\" was launched" % id))
		except:
			self.set_status(404)
			self.write(message(404, "Failed to launch workflow \"%s\"" % id))



class WorkflowResumeHandler(WorkflowLaunchHandler):

	resume = True



class WorkflowCancelHandler(tornado.web.RequestHandler):

	async def post(self, id):
		db = self.settings["db"]

		# get workflow
		workflow = await db.workflow_get(id)
		workflow = {**{ "pid": -1 }, **workflow}

		# terminate child process
		if workflow["pid"] != -1:
			try:
				os.kill(workflow["pid"], signal.SIGINT)
			except ProcessLookupError:
				pass

		try:
			# update workflow status
			workflow["status"] = "failed"
			workflow["pid"] = -1

			await db.workflow_update(id, workflow)

			self.set_status(200)
			self.write(message(200, "Workflow \"%s\" was canceled" % id))
		except:
			self.set_status(404)
			self.write(message(404, "Failed to cancel workflow \"%s\"" % id))



class WorkflowLogHandler(tornado.web.RequestHandler):

	async def get(self, id):
		db = self.settings["db"]

		# get workflow
		workflow = await db.workflow_get(id)

		# append log if it exists
		log_file = os.path.join(env.WORKFLOWS_DIR, id, ".workflow.log")

		if os.path.exists(log_file):
			f = open(log_file)
			log = "".join(f.readlines())
		else:
			log = ""

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode({ "_id": id, "status": workflow["status"], "log": log }))



class WorkflowDownloadHandler(tornado.web.StaticFileHandler):

	def parse_url_path(self, id):
		# provide output file if path is specified
		try:
			filename = self.get_query_argument("path")

		# otherwise provide the output data archive
		except tornado.web.MissingArgumentError:
			filename = "%s-output.tar.gz" % id

		self.set_header("Content-Disposition", "attachment; filename=\"%s\"" % filename)
		return os.path.join(id, filename)



class TaskQueryHandler(tornado.web.RequestHandler):

	async def get(self):
		page = int(self.get_query_argument("page", 0))
		page_size = int(self.get_query_argument("page_size", 100))

		db = self.settings["db"]
		tasks = await db.task_query(page, page_size)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(tasks))

	async def post(self):
		db = self.settings["db"]

		# make sure request body is valid
		try:
			task = tornado.escape.json_decode(self.request.body)
		except json.JSONDecodeError:
			self.set_status(422)
			self.write(message(422, "Ill-formatted JSON"))
			return

		# append id to task
		task["_id"] = str(bson.ObjectId())

		# save task
		await db.task_create(task)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode({ "_id": task["_id"] }))



class TaskEditHandler(tornado.web.RequestHandler):

	async def get(self, id):
		db = self.settings["db"]
		task = await db.task_get(id)

		self.set_status(200)
		self.set_header("Content-type", "application/json")
		self.write(tornado.escape.json_encode(task))



if __name__ == "__main__":
	# parse command-line options
	tornado.options.define("backend", default="json", help="Database backend to use (json or mongo)")
	tornado.options.define("json-filename", default="db.json", help="json file for json backend")
	tornado.options.define("mongo-hostname", default="localhost", help="mongodb service url for mongo backend")
	tornado.options.define("np", default=1, help="number of server processes")
	tornado.options.define("port", default=8080)
	tornado.options.parse_command_line()

	# initialize workflow directory
	os.makedirs(env.WORKFLOWS_DIR, exist_ok=True)

	# initialize api endpoints
	app = tornado.web.Application([
		(r"/api/workflows", WorkflowQueryHandler),
		(r"/api/workflows/0", WorkflowCreateHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)", WorkflowEditHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/upload", WorkflowUploadHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/launch", WorkflowLaunchHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/resume", WorkflowResumeHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/cancel", WorkflowCancelHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/log", WorkflowLogHandler),
		(r"/api/workflows/([a-zA-Z0-9-]+)/download", WorkflowDownloadHandler, dict(path=env.WORKFLOWS_DIR)),
		(r"/api/tasks", TaskQueryHandler),
		(r"/api/tasks/([a-zA-Z0-9-]+)", TaskEditHandler),
		(r"/(.*)", tornado.web.StaticFileHandler, dict(path="./client", default_filename="index.html"))
	])

	try:
		# spawn server processes
		server = tornado.httpserver.HTTPServer(app, max_buffer_size=1024 ** 3)
		server.bind(tornado.options.options.port)
		server.start(tornado.options.options.np)

		# connect to database
		if tornado.options.options.backend == "json":
			app.settings["db"] = backend.JSONBackend(tornado.options.options.json_filename)

		elif tornado.options.options.backend == "mongo":
			app.settings["db"] = backend.MongoBackend(tornado.options.options.mongo_hostname)

		else:
			raise KeyError("Backend must be either \'json\' or \'mongo\'")

		# start the event loop
		print("The API is listening on http://0.0.0.0:8080", flush=True)
		tornado.ioloop.IOLoop.current().start()

	except KeyboardInterrupt:
		tornado.ioloop.IOLoop.current().stop()
