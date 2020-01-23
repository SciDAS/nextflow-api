#!/usr/bin/env python3

import json
import motor.motor_tornado
import os
import tornado



WORKFLOWS_DIRS = {
	"k8s": "/workspace/_workflows",
	"local": "./_workflows",
	"pbspro": "./_workflows"
}

NXF_EXECUTOR = os.environ.get("NXF_EXECUTOR")
NXF_EXECUTOR = NXF_EXECUTOR if NXF_EXECUTOR else "local"
WORKFLOWS_DIR = WORKFLOWS_DIRS[NXF_EXECUTOR]



async def main():
	# connect to database
	client = motor.motor_tornado.MotorClient("mongodb://localhost:27017")
	db = client["nextflow_api"]

	# initialize workflow directory
	os.makedirs(WORKFLOWS_DIR, exist_ok=True)

	# get workflow ids
	workflow_ids = os.listdir(WORKFLOWS_DIR)
	workflow_ids = [id for id in workflow_ids if os.path.isdir(os.path.join(WORKFLOWS_DIR, id))]

	# get workflow objects
	config_files = ["%s/%s/config.json" % (WORKFLOWS_DIR, id) for id in workflow_ids]
	config_files = [f for f in config_files if os.path.exists(f)]
	workflows = [json.load(open(f)) for f in config_files]

	# insert each workflow into the database
	KEYS = [
		"pipeline",
		"name",
		"profiles",
		"revision",
		"input_dir",
		"output_dir",
		"date_created",
		"status"
	]

	for obj in workflows:
		workflow = {}
		workflow["_id"] = obj["id"]

		for key in KEYS:
			workflow[key] = obj[key]

		await db.workflows.insert_one(workflow)



if __name__ == "__main__":
	tornado.ioloop.IOLoop.current().run_sync(main)
