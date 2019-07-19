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
		.when("/", {
			templateUrl: "views/home.html",
			controller: "HomeCtrl"
		})
		.when("/workflow/:id", {
			templateUrl: "views/workflow.html",
			controller: "WorkflowCtrl"
		})
		.otherwise("/");
}]);



app.service("api", ["$http", function($http) {
	this.Workflow = {};

	this.Workflow.query = function() {
		return $http.get("/api/workflows")
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.get = function(id) {
		return $http.get("/api/workflows/" + id)
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.save = function(workflow) {
		return $http.post("/api/workflows/" + workflow.id, workflow)
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.launch = function(id) {
		return $http.post("/api/workflows/" + id + "/launch");
	};

	this.Workflow.resume = function(id) {
		return $http.post("/api/workflows/" + id + "/resume");
	};

	this.Workflow.log = function(id) {
		return $http.get("/api/workflows/" + id + "/log")
			.then(function(res) {
				return res.data;
			});
	};

	this.Workflow.remove = function(id) {
		return $http.delete("/api/workflows/" + id);
	};
}]);



const STATUS_COLORS = {
	"nascent": "success",
	"running": "warning",
	"completed": "success",
	"failed": "danger"
};



app.controller("HomeCtrl", ["$scope", "$route", "api", function($scope, $route, api) {
	$scope.STATUS_COLORS = STATUS_COLORS;
	$scope.workflows = [];

	$scope.delete = async function(w) {
		if ( !confirm("Are you sure you want to delete \"" + w.id + "\"?") ) {
			return;
		}

		await api.Workflow.remove(w.id);

		$route.reload();
	};

	// initialize
	const initialize = async function() {
		$scope.workflows = await api.Workflow.query();
		$scope.$apply();
	}

	initialize();
}]);



app.controller("WorkflowCtrl", ["$scope", "$interval", "$route", "api", "FileUploader", function($scope, $interval, $route, api, FileUploader) {
	$scope.STATUS_COLORS = STATUS_COLORS;
	$scope.workflow = {};

	$scope.uploader = new FileUploader({
		 url: "/api/workflows/" + $route.current.params.id + "/upload"
	});

	$scope.uploader.onCompleteAll = function() {
		$route.reload();
	};

	$scope.save = async function(workflow) {
		let res = await api.Workflow.save(workflow);

		$route.updateParams({ id: res.id });
		$scope.$apply();
	};

	$scope.launch = async function(id) {
		await api.Workflow.launch(id);

		$route.reload();
	};

	$scope.resume = async function(id) {
		await api.Workflow.resume(id);

		$route.reload();
	};

	// initialize
	const initialize = async function() {
		$scope.workflow = await api.Workflow.get($route.current.params.id);

		if ( $scope.workflow.status === "running" ) {
			$scope.intervalPromise = $interval(async function() {
				let res = await api.Workflow.log($scope.workflow.id);

				Object.assign($scope.workflow, res);

				if ( res.status !== "running" ) {
					$interval.cancel($scope.intervalPromise);
				}
				$scope.$apply();
			}, 2000, -1);
		}

		$scope.$apply();
	};

	initialize();
}]);
