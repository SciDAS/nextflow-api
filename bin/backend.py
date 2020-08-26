import json
import motor.motor_tornado
import pymongo



class Backend():
	def __init__(self):
		pass

	async def workflow_query(self, page, page_size):
		raise NotImplementedError()

	async def workflow_create(self, workflow):
		raise NotImplementedError()

	async def workflow_get(self, id):
		raise NotImplementedError()

	async def workflow_update(self, id, workflow):
		raise NotImplementedError()

	async def workflow_delete(self, id):
		raise NotImplementedError()

	async def task_query(self, page, page_size):
		raise NotImplementedError()

	async def task_create(self, task):
		raise NotImplementedError()

	async def task_get(self, id):
		raise NotImplementedError()



class JSONBackend(Backend):
	def __init__(self, filename):
		try:
			# load database from json file
			self._filename = filename
			self._db = json.load(open(filename))
		except FileNotFoundError:
			# initialize empty database if json file doesn't exist
			self._db = {
				"workflows": [],
				"tasks": []
			}

	async def workflow_query(self, page, page_size):
		# sort workflows by date_created in descending order
		self._db["workflows"].sort(key=lambda w: w["date_created"], reverse=True)

		# return the specified page of workflows
		return self._db["workflows"][(page * page_size) : ((page + 1) * page_size)]

	async def workflow_create(self, workflow):
		# append workflow to list of workflows
		self._db["workflows"].append(workflow)

		# save json file
		json.dump(self._db, open(self._filename, "w"))

	async def workflow_get(self, id):
		# search for workflow by id
		for w in self._db["workflows"]:
			if w["_id"] == id:
				return w

		# raise error if workflow wasn't found
		raise IndexError("Workflow was not found")

	async def workflow_update(self, id, workflow):
		# search for workflow by id and update it
		for i, w in enumerate(self._db["workflows"]):
			if w["_id"] == id:
				# update workflow
				self._db["workflows"][i] = workflow

				# save json file
				json.dump(self._db, open(self._filename, "w"))
				return

		# raise error if workflow wasn't found
		raise IndexError("Workflow was not found")

	async def workflow_delete(self, id):
		# search for workflow by id and delete it
		for i, w in enumerate(self._db["workflows"]):
			if w["_id"] == id:
				# delete workflow
				self._db["workflows"].pop(i)

				# save json file
				json.dump(self._db, open(self._filename, "w"))
				return

		# raise error if workflow wasn't found
		raise IndexError("Workflow was not found")

	async def task_query(self, page, page_size):
		# sort tasks by date_created in descending order
		self._db["tasks"].sort(key=lambda t: t["utcTime"], reverse=True)

		# return the specified page of workflows
		return self._db["tasks"][(page * page_size) : ((page + 1) * page_size)]

	async def task_create(self, task):
		# append workflow to list of workflows
		self._db["tasks"].append(task)

		# save json file
		json.dump(self._db, open(self._filename, "w"))

	async def task_get(self, id):
		# search for task by id
		for t in self._db["tasks"]:
			if t["_id"] == id:
				return t

		# raise error if task wasn't found
		raise IndexError("Task was not found")



class MongoBackend(Backend):
	def __init__(self, url):
		self._client = motor.motor_tornado.MotorClient(url)
		self._db = self._client["nextflow_api"]

	async def workflow_query(self, page, page_size):
		return await self._db.workflows \
			.find() \
			.sort("date_created", pymongo.DESCENDING) \
			.skip(page * page_size) \
			.to_list(length=page_size)

	async def workflow_create(self, workflow):
		return await self._db.workflows.insert_one(workflow)

	async def workflow_get(self, id):
		return await self._db.workflows.find_one({ "_id": id })

	async def workflow_update(self, id, workflow):
		return await self._db.workflows.replace_one({ "_id": id }, workflow)

	async def workflow_delete(self, id):
		return await self._db.workflows.delete_one({ "_id": id })

	async def task_query(self, page, page_size):
		return await self._db.tasks \
			.find({}, { "_id": 1, "runName": 1, "utcTime": 1, "event": 1 }) \
			.sort("utcTime", pymongo.DESCENDING) \
			.skip(page * page_size) \
			.to_list(length=page_size)

	async def task_create(self, task):
		return await self._db.tasks.insert_one(task)

	async def task_get(self, id):
		return await self._db.tasks.find_one({ "_id": id })
