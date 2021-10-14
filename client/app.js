'use strict'

const app = angular.module('app', [
	'ngRoute',
	'angularFileUpload'
])



app.config(['$compileProvider', function($compileProvider) {
	$compileProvider.debugInfoEnabled(false)
}])



app.config(['$routeProvider', function($routeProvider) {
	$routeProvider
		.when('/', { redirectTo: '/workflows' })
		.when('/workflows', {
			templateUrl: 'views/workflows.html',
			controller: 'WorkflowsCtrl'
		})
		.when('/workflows/:id', {
			templateUrl: 'views/workflow.html',
			controller: 'WorkflowCtrl'
		})
		.when('/tasks', {
			templateUrl: 'views/tasks.html',
			controller: 'TasksCtrl'
		})
		.when('/tasks/:id', {
			templateUrl: 'views/task.html',
			controller: 'TaskCtrl'
		})
		.when('/visualizer', {
			templateUrl: 'views/visualizer.html',
			controller: 'VisualizerCtrl'
		})
		.when('/model', {
			templateUrl: 'views/model.html',
			controller: 'ModelCtrl'
		})
		.otherwise('/')
}])



app.service('alert', ['$interval', function($interval) {
	this.alerts = []

	const self = this
	let count = 0

	const addAlert = function(type, header, message) {
		let id = count
		let promise = $interval(function() {
			let index = self.alerts.findIndex(function(alert) {
				return (alert.id === id)
			})

			self.alerts.splice(index, 1)
		}, 10000, 1)

		self.alerts.push({
			id: id,
			type: type,
			header: header,
			message: message,
			promise: promise
		})
		count++
	}

	this.success = function(message) {
		addAlert('success', null, message)
	}

	this.info = function(message) {
		addAlert('info', null, message)
	}

	this.warning = function(message) {
		addAlert('warning', null, message)
	}

	this.error = function(message) {
		addAlert('danger', 'Error: ', message)
	}

	this.remove = function(index) {
		$interval.cancel(self.alerts[index].promise)

		self.alerts.splice(index, 1)
	}
}])



app.service('api', ['$http', '$q', function($http, $q) {
	function httpRequest(method, url, params, data) {
		return $http({
			method: method,
			url: window.location.pathname + url,
			params: params,
			data: data
		}).then(function(res) {
			return res.data
		}, function(res) {
			return $q.reject(res.data)
		})
	}

	this.Workflow = {}

	this.Workflow.query = function(page) {
		return httpRequest('get', 'api/workflows', { page: page })
	}

	this.Workflow.get = function(id) {
		return httpRequest('get', `api/workflows/${id}`)
	}

	this.Workflow.save = function(workflow) {
		return httpRequest('post', `api/workflows/${workflow._id}`, null, workflow)
	}

	this.Workflow.launch = function(id) {
		return httpRequest('post', `api/workflows/${id}/launch`)
	}

	this.Workflow.resume = function(id) {
		return httpRequest('post', `api/workflows/${id}/resume`)
	}

	this.Workflow.cancel = function(id) {
		return httpRequest('post', `api/workflows/${id}/cancel`)
	}

	this.Workflow.log = function(id) {
		return httpRequest('get', `api/workflows/${id}/log`)
	}

	this.Workflow.remove = function(id) {
		return httpRequest('delete', `api/workflows/${id}`)
	}

	this.Task = {}

	this.Task.query = function(page) {
		return httpRequest('get', 'api/tasks', { page: page })
	}

	this.Task.query_pipelines = function() {
		return httpRequest('get', `api/tasks/pipelines`)
	}

	this.Task.query_pipeline = function(pipeline) {
		return httpRequest('get', `api/tasks/pipelines/${pipeline}`)
	}

	this.Task.archive = function(pipeline) {
		return httpRequest('get', `api/tasks/archive/${pipeline}`)
	}

	this.Task.get = function(id) {
		return httpRequest('get', `api/tasks/${id}`)
	}

	this.Task.log = function(id) {
		return httpRequest('get', `api/tasks/${id}/log`)
	}

	this.Task.visualize = function(pipeline, process, args) {
		return httpRequest('post', `api/tasks/visualize`, null, {
			pipeline,
			process,
			args
		})
	}

	this.Model = {}

	this.Model.train = function(pipeline, process, args) {
		return httpRequest('post', `api/model/train`, null, {
			pipeline,
			process,
			args
		})
	}

	this.Model.get_config = function(pipeline, process, target) {
		return httpRequest('get', `api/model/config`, {
			pipeline,
			process,
			target
		})
	}

	this.Model.predict = function(pipeline, process, target, inputs) {
		return httpRequest('post', `api/model/predict`, null, {
			pipeline,
			process,
			target,
			inputs
		})
	}
}])



app.controller('MainCtrl', ['$scope', 'alert', function($scope, alert) {
	$scope.alert = alert
}])



const STATUS_COLORS = {
	'nascent': 'primary',
	'running': 'warning',
	'completed': 'success',
	'failed': 'danger'
}



app.controller('WorkflowsCtrl', ['$scope', '$route', 'alert', 'api', function($scope, $route, alert, api) {
	$scope.STATUS_COLORS = STATUS_COLORS
	$scope.page = 0
	$scope.workflows = []

	$scope.query = function(page) {
		api.Workflow.query(page)
			.then(function(workflows) {
				$scope.page = page
				$scope.workflows = workflows
			}, function() {
				alert.error('Failed to query workflow instances.')
			})
	}

	$scope.delete = function(w) {
		if ( !confirm(`Are you sure you want to delete \"${w._id}\"?`) ) {
			return
		}

		api.Workflow.remove(w._id)
			.then(function() {
				alert.success('Workflow instance deleted.')
				$route.reload()
			}, function() {
				alert.error('Failed to delete workflow instance.')
			})
	}

	// initialize
	$scope.query(0)
}])



app.controller('WorkflowCtrl', ['$scope', '$interval', '$route', 'alert', 'api', 'FileUploader', function($scope, $interval, $route, alert, api, FileUploader) {
	$scope.STATUS_COLORS = STATUS_COLORS
	$scope.workflow = {}

	$scope.uploader = new FileUploader({
		 url: `${window.location.pathname}api/workflows/${$route.current.params.id}/upload`
	})

	$scope.uploader.onCompleteAll = function() {
		alert.success('All input files uploaded.')
		$scope.uploading = false
		$route.reload()
	}

	$scope.uploader.onErrorItem = function() {
		alert.error('Failed to upload input files.')
		$scope.uploading = false
	}

	$scope.save = function(workflow) {
		api.Workflow.save(workflow)
			.then(function(res) {
				alert.success('Workflow instance saved.')
				$route.updateParams({ id: res._id })
			}, function() {
				alert.error('Failed to save workflow instance.')
			})
	}

	$scope.upload = function() {
		$scope.uploading = true
		$scope.uploader.uploadAll()
	}

	$scope.launch = function(id) {
		$scope.launching = true

		api.Workflow.launch(id)
			.then(function() {
				alert.success('Workflow instance launched.')
				$scope.workflow.status = ''
				$scope.workflow.log = ''
				$scope.launching = false
				$scope.fetchLog()
			}, function() {
				alert.error('Failed to launch workflow instance.')
				$scope.launching = false
			})
	}

	$scope.resume = function(id) {
		$scope.resuming = true

		api.Workflow.resume(id)
			.then(function() {
				alert.success('Workflow instance resumed.')
				$scope.workflow.status = ''
				$scope.workflow.log = ''
				$scope.resuming = false
				$scope.fetchLog()
			}, function() {
				alert.error('Failed to resume workflow instance.')
				$scope.resuming = false
			})
	}

	$scope.cancel = function(id) {
		$scope.cancelling = true

		api.Workflow.cancel(id)
			.then(function() {
				alert.success('Workflow instance canceled.')
				$scope.cancelling = false
				$route.reload()
			}, function() {
				alert.error('Failed to cancel workflow instance.')
				$scope.cancelling = false
			})
	}

	$scope.fetchLog = function() {
		if ( $scope.intervalPromise ) {
			return
		}

		$scope.intervalPromise = $interval(function() {
			api.Workflow.log($scope.workflow._id)
				.then(function(res) {
					Object.assign($scope.workflow, res)

					if ( res.status !== 'running' ) {
						$interval.cancel($scope.intervalPromise)
						$scope.intervalPromise = undefined
					}
				})
		}, 2000, -1)
	}

	$scope.$on('$destroy', function() {
		if ( angular.isDefined($scope.intervalPromise) ) {
			$interval.cancel($scope.intervalPromise)
		}
	})

	// initialize
	api.Workflow.get($route.current.params.id)
		.then(function(workflow) {
			$scope.workflow = workflow

			if ( $scope.workflow._id !== '0' ) {
				$scope.fetchLog()
			}
		}, function() {
			alert.error('Failed to load workflow.')
		})
}])



app.controller('TasksCtrl', ['$scope', 'alert', 'api', function($scope, alert, api) {
	$scope.page = 0
	$scope.tasks = []

	$scope.query_pipelines = function() {
		api.Task.query_pipelines()
			.then(function(pipelines) {
				$scope.pipelines = pipelines
			}, function() {
				alert.error('Failed to query pipelines.')
			})
	}

	$scope.query_tasks = function(page) {
		api.Task.query(page)
			.then(function(tasks) {
				$scope.page = page
				$scope.tasks = tasks
			}, function() {
				alert.error('Failed to query tasks.')
			})
	}

	$scope.archive = function(pipeline) {
		$scope.archiving = true

		api.Task.archive(pipeline)
			.then(function() {
				$scope.archiving = false
				$scope.archive_success = true

				alert.success('Archive was created.')
			}, function() {
				$scope.archiving = false
				$scope.archive_success = false

				alert.error('Failed to create archive.')
			})
	}

	// initialize
	$scope.query_pipelines()
	$scope.query_tasks(0)
}])



app.controller('TaskCtrl', ['$scope', '$route', 'alert', 'api', function($scope, $route, alert, api) {
	$scope.task = {}
	$scope.task_out = ''
	$scope.task_err = ''

	$scope.fetchLog = function() {
		api.Task.log($route.current.params.id)
			.then(function(res) {
				$scope.task_out = res.out
				$scope.task_err = res.err
			}, function() {
				alert.error('Failed to fetch task logs.')
			})
	}

	// initialize
	api.Task.get($route.current.params.id)
		.then(function(task) {
			$scope.task = task
		}, function() {
			alert.error('Failed to load task.')
		})
}])



app.controller('VisualizerCtrl', ['$scope', 'alert', 'api', function($scope, alert, api) {
	$scope.args = {
		selectors: 'exit=0',
		height: 3,
		aspect: 1
	}
	$scope.columns = []
	$scope.merge_columns = []

	$scope.query_pipelines = function() {
		api.Task.query_pipelines()
			.then(function(pipelines) {
				$scope.pipelines = pipelines
			}, function() {
				alert.error('Failed to query pipelines.')
			})
	}

	$scope.query_dataset = function(pipeline) {
		$scope.querying = true

		api.Task.query_pipeline(pipeline)
			.then(function(data) {
				let process_names = Object.keys(data)
				let process_columns = process_names.reduce((prev, process) => {
					let tasks = data[process]
					let columns = new Set(tasks.reduce((p, t) => p.concat(Object.keys(t)), []))
					prev[process] = Array.from(columns)
					return prev
				}, {})

				$scope.querying = false
				$scope.pipeline_data = data
				$scope.process_names = process_names
				$scope.process_columns = process_columns
			}, function() {
				$scope.querying = false
				alert.error('Failed to query pipeline tasks.')
			})
	}

	$scope.update_columns = function(process_columns, process, merge_process) {
		let array1 = process ? process_columns[process] : []
		let array2 = merge_process ? process_columns[merge_process] : []

		$scope.columns = Array.from(new Set(array1.concat(array2)))
		$scope.merge_columns = array1.filter(value => array2.includes(value));
	}

	$scope.visualize = function(pipeline, process, args) {
		$scope.visualizing = true

		api.Task.visualize(pipeline, process, args)
			.then(function(image_data) {
				$scope.visualizing = false
				$scope.visualize_success = true
				$scope.image_data = image_data
				alert.success('Visualiation was created.')
			}, function() {
				$scope.visualizing = false
				$scope.visualize_success = false
				alert.error('Failed to visualize data.')
			})
	}

	// initialize
	$scope.query_pipelines()
}])



app.controller('ModelCtrl', ['$scope', 'alert', 'api', function($scope, alert, api) {
	$scope.args = {
		merge_process: null,
		inputs: [],
		target: null,
		scaler: 'maxabs',
		selectors: 'exit=0',
		hidden_layer_sizes: '128 128 128',
		epochs: 200
	}
	$scope.columns = []
	$scope.merge_columns = []

	$scope.train = {}
	$scope.predict = {}

	$scope.query_pipelines = function() {
		api.Task.query_pipelines()
			.then(function(pipelines) {
				$scope.pipelines = pipelines
			}, function() {
				alert.error('Failed to query pipelines.')
			})
	}

	$scope.query_dataset = function(pipeline) {
		$scope.querying = true

		api.Task.query_pipeline(pipeline)
			.then(function(data) {
				let process_names = Object.keys(data)
				let process_columns = process_names.reduce((prev, process) => {
					let tasks = data[process]
					let columns = new Set(tasks.reduce((p, t) => p.concat(Object.keys(t)), []))
					prev[process] = Array.from(columns)
					return prev
				}, {})

				$scope.querying = false
				$scope.pipeline_data = data
				$scope.process_names = process_names
				$scope.process_columns = process_columns
			}, function() {
				$scope.querying = false
				alert.error('Failed to query pipeline tasks.')
			})
	}

	$scope.update_columns = function(process_columns, process, merge_process) {
		let array1 = process ? process_columns[process] : []
		let array2 = merge_process ? process_columns[merge_process] : []

		$scope.columns = Array.from(new Set(array1.concat(array2)))
		$scope.merge_columns = array1.filter(value => array2.includes(value));
	}

	$scope.train = function(pipeline, process, args) {
		$scope.training = true

		api.Model.train(pipeline, process, args)
			.then(function(results) {
				$scope.training = false
				$scope.train.results = results
				alert.success('Model was trained.')
			}, function() {
				$scope.training = false
				alert.error('Failed to train model.')
			})
	}

	$scope.get_config = function(pipeline, process, target) {
		api.Model.get_config(pipeline, process, target)
			.then(function(config) {
				$scope.config = config
				$scope.predict.options = config.inputs
				$scope.predict.inputs = Object.keys(config.inputs).reduce((prev, input) => {
					prev[input] = null
					return prev
				}, {})

				console.log($scope.predict)
			}, function() {
				alert.error('Failed to get model config.')
			})
	}

	$scope.predict = function(pipeline, process, target, inputs) {
		$scope.predicting = true

		api.Model.predict(pipeline, process, target, inputs)
			.then(function(results) {
				$scope.predicting = false
				$scope.predict.results = results
				alert.success('Performed model prediction.')
			}, function() {
				$scope.predicting = false
				alert.error('Failed to perform model prediction.')
			})
	}

	// initialize
	$scope.query_pipelines()
}])
