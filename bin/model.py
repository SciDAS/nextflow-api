import json
import numpy as np
import os
import pandas as pd
import pickle
import sklearn.metrics
import sklearn.model_selection
import sklearn.pipeline
import sklearn.preprocessing
from tensorflow import keras

import env
import utils



def parse_transforms(arg):
	tokens = arg.split(':')
	return { 'name': tokens[0], 'transforms': tokens[1:] }



def create_mlp(input_shape, hidden_layer_sizes=[10], activation='relu'):
	def build_fn():
		# create a 3-layer neural network
		x_input = keras.Input(shape=input_shape)

		x = x_input
		for units in hidden_layer_sizes:
			x = keras.layers.Dense(units=units, activation=activation)(x)

		y_output = keras.layers.Dense(units=1)(x)

		mlp = keras.models.Model(x_input, y_output)

		# compile the model
		mlp.compile(optimizer='adam', loss='mean_absolute_percentage_error')

		return mlp

	return utils.KerasRegressor(
		build_fn=build_fn,
		batch_size=32,
		epochs=200,
		validation_split=0.1,
		verbose=False
	)



def mean_absolute_percentage_error(y_true, y_pred):
	y_true = np.array(y_true)
	y_pred = np.array(y_pred)
	return 100 * np.mean(np.abs((y_true - y_pred) / y_true))



def evaluate_once(model, X, y, train_size=0.8):
	# create train/test split
	X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(X, y, test_size=1 - train_size)

	# train model
	model.fit(X_train, y_train)

	# evaluate model
	y_pred = model.predict(X_test)
	score = mean_absolute_percentage_error(y_test, y_pred)

	return score



def evaluate_trials(model, X, y, train_size=0.8, n_trials=5):
	return [evaluate_once(model, X, y, train_size=train_size) for i in range(n_trials)]



def evaluate_cv(model, X, y, cv=5):
	scorer = sklearn.metrics.make_scorer(mean_absolute_percentage_error)
	scores = sklearn.model_selection.cross_val_score(model, X, y, scoring=scorer, cv=cv, n_jobs=-1)

	return scores



def train(df, args):
	defaults = {
		'scaler': 'maxabs',
		'cv': 5,
		'hidden_layer_sizes': [128, 128, 128]
	}

	args = {**defaults, **args}

	# parse input and output transforms
	inputs = [parse_transforms(arg) for arg in args['inputs']]
	output = parse_transforms(args['output'])

	# select only tasks that completed successfully
	df = df[df['exit'] == 0]

	# extract input/output data from trace data
	try:
		X = df[[c['name'] for c in inputs]]
		y = df[output['name']]
	except KeyError:
		raise KeyError('error: one or more input/output variables are not in the dataset')

	# one-hot encode categorical inputs
	onehot_columns = [c['name'] for c in inputs if 'onehot' in c['transforms']]

	X = pd.get_dummies(X, columns=onehot_columns, drop_first=False)

	# apply transforms to output
	for transform in output['transforms']:
		try:
			t = utils.transforms[transform]
			y = t.transform(y)
		except:
			raise KeyError('error: output transform %s not recognized' % (transform))

	# select scaler
	if args['scaler'] != None:
		scalers = {
			'maxabs': sklearn.preprocessing.MaxAbsScaler,
			'minmax': sklearn.preprocessing.MinMaxScaler,
			'standard': sklearn.preprocessing.StandardScaler
		}
		Scaler = scalers[args['scaler']]

	# create regressor
	regressor = create_mlp(X.shape[1], hidden_layer_sizes=args['hidden_layer_sizes'])

	# create model
	model = sklearn.pipeline.Pipeline([
		('scaler', Scaler()),
		('regressor', regressor)
	])

	# create model configuration
	config = {
		'inputs': list(X.columns),
		'output-transforms': output['transforms']
	}

	# train and evaluate model
	print('training model')

	scores = evaluate_cv(model, X, y, cv=args['cv'])

	# save trained model
	print('saving model to file')

	# train model on full dataset
	model.fit(X, y)

	# workaround for keras models
	try:
		model.named_steps['regressor'].build_fn = None
	except:
		pass

	# save model to file
	f = open('%s/%s.pkl' % (env.MODELS_DIR, args['model_name']), 'wb')
	pickle.dump(model, f)

	# save model configuration
	f = open('%s/%s.json' % (env.MODELS_DIR, args['model_name']), 'w')
	json.dump(config, f)

	# return results
	return {
		'mape': scores.mean()
	}



def predict(args):
	# load model
	f = open('%s/%s.pkl' % (env.MODELS_DIR, args['model_name']), 'rb')
	model = pickle.load(f)

	# load model configuration
	f = open('%s/%s.json' % (env.MODELS_DIR, args['model_name']), 'r')
	config = json.load(f)

	# parse inputs
	x_input = [args['inputs'][column] for column in config['inputs']]

	# perform inference
	X = np.array([x_input])
	y = model.predict(X)

	# apply transforms to output if specified
	for transform in config['output-transforms']:
		try:
			t = utils.transforms[transform]
			y = t.inverse_transform(y)
		except:
			raise KeyError('error: output transform %s not recognized' % (transform))

	# return results
	return {
		'output': float(y)
	}