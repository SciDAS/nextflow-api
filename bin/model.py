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



def select_rows_by_values(df, column, values):
	return pd.DataFrame().append([df[df[column].astype(str) == v] for v in values], sort=False)



def is_categorical(df, column):
	return column != None and df[column].dtype.kind in 'OSUV'



def create_mlp(input_shape, hidden_layer_sizes=[], activation='relu', batch_size=32, epochs=200):
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
		batch_size=batch_size,
		epochs=epochs,
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
		'selectors': [],
		'scaler': 'maxabs',
		'cv': 5,
		'hidden_layer_sizes': [128, 128, 128],
		'epochs': 200
	}

	args = {**defaults, **args}

	# apply selectorss to dataframe
	for selector in args['selectors']:
		# parse column and selected values
		column, values = selector.split('=')
		values = values.split(',')

		# select rows from dataframe
		if values != None and len(values) > 0:
			df = select_rows_by_values(df, column, values)

	# extract input/output data from trace data
	try:
		X = df[[c['name'] for c in args['inputs']]]
		y = df[args['output']['name']]
	except:
		raise RuntimeError('error: one or more input/output variables are not in the dataset')

	# one-hot encode categorical inputs
	onehot_columns = []

	for c in args['inputs']:
		if is_categorical(X, c['name']):
			c['categories'] = X[c['name']].unique().tolist()
			onehot_columns.append(c['name'])

	X = pd.get_dummies(X, columns=onehot_columns, drop_first=False)

	# apply output transforms
	for transform in args['output']['transforms']:
		try:
			t = utils.transforms[transform]
			y = t.transform(y)
		except:
			raise RuntimeError('error: output transform %s not recognized' % (transform))

	# select scaler
	if args['scaler'] != None:
		scalers = {
			'maxabs': sklearn.preprocessing.MaxAbsScaler,
			'minmax': sklearn.preprocessing.MinMaxScaler,
			'standard': sklearn.preprocessing.StandardScaler
		}
		Scaler = scalers[args['scaler']]

	# create regressor
	regressor = create_mlp(X.shape[1], hidden_layer_sizes=args['hidden_layer_sizes'], epochs=args['epochs'])

	# create model
	model = sklearn.pipeline.Pipeline([
		('scaler', Scaler()),
		('regressor', regressor)
	])

	# save order of input columns
	args['columns'] = list(X.columns)

	# train and evaluate model
	scores = evaluate_cv(model, X, y, cv=args['cv'])

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

	# save args to file
	f = open('%s/%s.json' % (env.MODELS_DIR, args['model_name']), 'w')
	json.dump(args, f)

	# return results
	return {
		'y_true': y,
		'y_test': model.predict(X),
		'mape': scores.mean()
	}



def predict(model_name, inputs):
	# load model
	f = open('%s/%s.pkl' % (env.MODELS_DIR, model_name), 'rb')
	model = pickle.load(f)

	# load model configuration
	f = open('%s/%s.json' % (env.MODELS_DIR, model_name), 'r')
	args = json.load(f)

	# parse inputs
	x_input = {}

	for column in inputs:
		if 'categories' in column:
			for v in column['categories']:
				x_input['%s_%s' % (column['name'], v)] = (v == column['value'])
		else:
			x_input[column['name']] = column['value']

	x_input = [float(x_input[c]) for c in args['columns']]

	# perform inference
	X = np.array([x_input])
	y = model.predict(X)

	# apply transforms to output if specified
	for transform in args['output']['transforms']:
		try:
			t = utils.transforms[transform]
			y = t.inverse_transform(y)
		except:
			raise RuntimeError('error: output transform %s not recognized' % (transform))

	# return results
	return {
		args['output']['name']: float(y)
	}