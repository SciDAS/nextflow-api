"use strict";

const app = angular.module("app", [
	"ngRoute",
	"angularFileUpload"
]);



app.config(["$compileProvider", function($compileProvider) {
	$compileProvider.debugInfoEnabled(false);
}]);



app.config(["$routeProvider", function($routeProvider) {
	$routeProvider
		.when("/", { redirectTo: "/workflows" })
		.when("/workflows", {
			templateUrl: "views/workflows.html",
			controller: "WorkflowsCtrl"
		})
		.when("/workflows/:id", {
			templateUrl: "views/workflow.html",
			controller: "WorkflowCtrl"
		})
		.when("/tasks", {
			templateUrl: "views/tasks.html",
			controller: "TasksCtrl"
		})
		.when("/tasks/:id", {
			templateUrl: "views/task.html",
			controller: "TaskCtrl"
		})
		.otherwise("/");
}]);



app.service("alert", ["$interval", function($interval) {
	this.alerts = [];

	const self = this;
	let count = 0;

	const addAlert = function(type, header, message) {
		let id = count;
		let promise = $interval(function() {
			let index = self.alerts.findIndex(function(alert) {
				return (alert.id === id);
			});

			self.alerts.splice(index, 1);
		}, 10000, 1);

		self.alerts.push({
			id: id,
			type: type,
			header: header,
			message: message,
			promise: promise
		});
		count++;
	};

	this.success = function(message) {
		addAlert("success", null, message);
	};

	this.info = function(message) {
		addAlert("info", null, message);
	};

	this.warning = function(message) {
		addAlert("warning", null, message);
	};

	this.error = function(message) {
		addAlert("danger", "Error: ", message);
	};

	this.remove = function(index) {
		$interval.cancel(self.alerts[index].promise);

		self.alerts.splice(index, 1);
	};
}]);



app.service("api", ["$http", function($http) {
	this.Workflow = {};

	this.Workflow.query = function(page) {
		return $http.get(window.location.pathname + "api/workflows", { params: { page: page } })
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.get = function(id) {
		return $http.get(window.location.pathname + "api/workflows/" + id)
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.save = function(workflow) {
		return $http.post(window.location.pathname + "api/workflows/" + workflow._id, workflow)
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.launch = function(id) {
		return $http.post(window.location.pathname + "api/workflows/" + id + "/launch");
	};

	this.Workflow.resume = function(id) {
		return $http.post(window.location.pathname + "api/workflows/" + id + "/resume");
	};

	this.Workflow.cancel = function(id) {
		return $http.post(window.location.pathname + "api/workflows/" + id + "/cancel");
	};

	this.Workflow.log = function(id) {
		return $http.get(window.location.pathname + "api/workflows/" + id + "/log")
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.remove = function(id) {
		return $http.delete(window.location.pathname + "api/workflows/" + id);
	};

	this.Task = {};

	this.Task.query = function(page) {
		return $http.get(window.location.pathname + "api/tasks", { params: { page: page } })
			.then(function(res) {
				return res.data;
			});
	};

	this.Task.get = function(id) {
		return $http.get(window.location.pathname + "api/tasks/" + id)
			.then(function(res) {
				return res.data;
			});
	};
}]);



app.controller("MainCtrl", ["$scope", "alert", function($scope, alert) {
	$scope.alert = alert;
}]);



const STATUS_COLORS = {
	"nascent": "success",
	"running": "warning",
	"completed": "success",
	"failed": "danger"
};



app.controller("WorkflowsCtrl", ["$scope", "$route", "alert", "api", function($scope, $route, alert, api) {
	$scope.STATUS_COLORS = STATUS_COLORS;
	$scope.page = 0;
	$scope.workflows = [];

	$scope.query = function(page) {
		api.Workflow.query(page)
			.then(function(workflows) {
				$scope.page = page;
				$scope.workflows = workflows;
			}, function() {
				alert.error("Failed to query workflow instances.");
			});
	};

	$scope.delete = function(w) {
		if ( !confirm("Are you sure you want to delete \"" + w._id + "\"?") ) {
			return;
		}

		api.Workflow.remove(w._id)
			.then(function() {
				alert.success("Workflow instance deleted.");
				$route.reload();
			}, function() {
				alert.error("Failed to delete workflow instance.");
			});
	};

	// initialize
	$scope.query(0);
}]);



app.controller("WorkflowCtrl", ["$scope", "$interval", "$route", "alert", "api", "FileUploader", function($scope, $interval, $route, alert, api, FileUploader) {
	$scope.STATUS_COLORS = STATUS_COLORS;
	$scope.workflow = {};

	$scope.uploader = new FileUploader({
		 url: window.location.pathname + "api/workflows/" + $route.current.params.id + "/upload"
	});

	$scope.uploader.onCompleteAll = function() {
		alert.success("All input files uploaded.");
		$route.reload();
	};

	$scope.uploader.onErrorItem = function() {
		alert.error("Failed to upload input files.");
	};

	$scope.save = function(workflow) {
		api.Workflow.save(workflow)
			.then(function(res) {
				alert.success("Workflow instance saved.");
				$route.updateParams({ id: res._id });
			}, function() {
				alert.error("Failed to save workflow instance.");
			});
	};

	$scope.launch = function(id) {
		$scope.launching = true;

		api.Workflow.launch(id)
			.then(function() {
				alert.success("Workflow instance launched.");
				$scope.workflow.status = "";
				$scope.workflow.log = "";
				$scope.launching = false;
				$scope.fetchLog();
			}, function() {
				alert.error("Failed to launch workflow instance.");
				$scope.launching = false;
			});
	};

	$scope.resume = function(id) {
		$scope.resuming = true;

		api.Workflow.resume(id)
			.then(function() {
				alert.success("Workflow instance resumed.");
				$scope.workflow.status = "";
				$scope.workflow.log = "";
				$scope.resuming = false;
				$scope.fetchLog();
			}, function() {
				alert.error("Failed to resume workflow instance.");
				$scope.resuming = false;
			});
	};

	$scope.cancel = function(id) {
		$scope.cancelling = true;

		api.Workflow.cancel(id)
			.then(function() {
				alert.success("Workflow instance canceled.");
				$scope.cancelling = false;
				$route.reload();
			}, function() {
				alert.error("Failed to cancel workflow instance.");
				$scope.cancelling = false;
			});
	};

	$scope.fetchLog = function() {
		if ( $scope.intervalPromise ) {
			return;
		}

		$scope.intervalPromise = $interval(function() {
			api.Workflow.log($scope.workflow._id)
				.then(function(res) {
					Object.assign($scope.workflow, res);

					if ( res.status !== "running" ) {
						$interval.cancel($scope.intervalPromise);
						$scope.intervalPromise = undefined;
					}
				});
		}, 2000, -1);
	};

	$scope.$on("$destroy", function() {
		if ( angular.isDefined($scope.intervalPromise) ) {
			$interval.cancel($scope.intervalPromise);
		}
	});

	// initialize
	api.Workflow.get($route.current.params.id)
		.then(function(workflow) {
			$scope.workflow = workflow;

			if ( $scope.workflow._id !== "0" ) {
				$scope.fetchLog();
			}
		}, function() {
			alert.error("Failed to load workflow.");
		});
}]);



app.controller("TasksCtrl", ["$scope", "alert", "api", function($scope, alert, api) {
	$scope.page = 0;
	$scope.tasks = [];

	$scope.query = function(page) {
		api.Task.query(page)
			.then(function(tasks) {
				$scope.page = page;
				$scope.tasks = tasks;
			}, function() {
				alert.error("Failed to query tasks.");
			});
	};

	// initialize
	$scope.query(0);
}]);



app.controller("TaskCtrl", ["$scope", "$route", "alert", "api", function($scope, $route, alert, api) {
	$scope.task = {};

	// initialize
	api.Task.get($route.current.params.id)
		.then(function(task) {
			$scope.task = task;
		}, function() {
			alert.error("Failed to load task.");
		});
}]);
