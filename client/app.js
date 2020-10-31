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
		return httpRequest('get', 'api/workflows/' + id)
	}

	this.Workflow.save = function(workflow) {
		return httpRequest('post', 'api/workflows/' + workflow._id, null, workflow)
	}

	this.Workflow.launch = function(id) {
		return httpRequest('post', 'api/workflows/' + id + '/launch')
	}

	this.Workflow.resume = function(id) {
		return httpRequest('post', 'api/workflows/' + id + '/resume')
	}

	this.Workflow.cancel = function(id) {
		return httpRequest('post', 'api/workflows/' + id + '/cancel')
	}

	this.Workflow.log = function(id) {
		return httpRequest('get', 'api/workflows/' + id + '/log')
	}

	this.Workflow.remove = function(id) {
		return httpRequest('delete', 'api/workflows/' + id)
	}

	this.Task = {}

	this.Task.query = function(page) {
		return httpRequest('get', 'api/tasks', { page: page })
	}

	this.Task.get = function(id) {
		return httpRequest('get', 'api/tasks/' + id)
	}

	this.Task.query_csv = function(pipeline) {
		return httpRequest('post', 'api/tasks-csv/' + pipeline)
	}
}])



app.controller('MainCtrl', ['$scope', 'alert', function($scope, alert) {
	$scope.alert = alert
}])



const STATUS_COLORS = {
	'nascent': 'success',
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
		if ( !confirm('Are you sure you want to delete \"' + w._id + '\"?') ) {
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
		 url: window.location.pathname + 'api/workflows/' + $route.current.params.id + '/upload'
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

	$scope.query = function(page) {
		api.Task.query(page)
			.then(function(tasks) {
				$scope.page = page
				$scope.tasks = tasks
			}, function() {
				alert.error('Failed to query tasks.')
			})
	}

	$scope.query_csv = function(pipeline) {
		$scope.querying = true

		api.Task.query_csv(pipeline)
			.then(function(tasks) {
				$scope.querying = false
				$scope.query_success = pipeline

				alert.success('Query was completed.')
			}, function() {
				$scope.querying = false
				$scope.query_success = null

				alert.error('Failed to perform query.')
			})
	}

	// initialize
	$scope.query(0)
}])



app.controller('TaskCtrl', ['$scope', '$route', 'alert', 'api', function($scope, $route, alert, api) {
	$scope.task = {}

	// initialize
	api.Task.get($route.current.params.id)
		.then(function(task) {
			$scope.task = task
		}, function() {
			alert.error('Failed to load task.')
		})
}])
