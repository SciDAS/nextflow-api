"use strict";

var app = angular.module("app", [
	"ngRoute"
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
		return $http.post("/api/workflows/" + workflow.id, workflow);
	};

	this.Workflow.launch = function(id) {
		return $http.post("/api/workflows/" + id + "/launch");
	};

	this.Workflow.remove = function(id) {
		return $http.delete("/api/workflows/" + id);
	};
}]);



app.controller("HomeCtrl", ["$scope", "$route", "api", function($scope, $route, api) {
	$scope.workflows = [];

	$scope.launch = function(w) {
		api.Workflow.launch(w.id)
			.then(function() {
				$route.reload();
			})
	};

	$scope.delete = function(w) {
		if ( !confirm("Are you sure you want to delete \"" + w.id + "\"?") ) {
			return;
		}

		api.Workflow.remove(w.id)
			.then(function() {
				$route.reload();
			})
	};

	// initialize
	api.Workflow.query()
		.then(function(workflows) {
			$scope.workflows = workflows;
		});
}]);



app.controller("WorkflowCtrl", ["$scope", "$location", "$q", "$routeParams", "api", function($scope, $location, $q, $routeParams, api) {
	$scope.workflow = {};

	$scope.save = function(workflow) {
		api.Workflow.save(workflow)
			.then(function() {
				$location.url("/");
			});
	};

	// initialize
	api.Workflow.get($routeParams.id)
		.then(function(workflow) {
			$scope.workflow = workflow;
		});
}]);
