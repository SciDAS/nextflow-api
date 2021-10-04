import copy
import dill as pickle
import forestci
import h5py
import io
import json
import numpy as np
import pandas as pd
import scipy.stats
import sklearn.base
import sklearn.dummy
import sklearn.ensemble
import sklearn.metrics
import sklearn.model_selection
import sklearn.pipeline
import sklearn.preprocessing
from tensorflow import keras

import env



def check_std(y_pred):
	if isinstance(y_pred, tuple):
		return y_pred
	else:
		return y_pred, np.zeros_like(y_pred)



def predict_intervals(y_bar, y_std, ci=0.95):
	# compute z score
	_, n_stds = scipy.stats.norm.interval(ci)

	# compute intervals
	y_lower = y_bar - n_stds * y_std
	y_upper = y_bar + n_stds * y_std

	return y_lower, y_upper



class KerasRegressor(keras.wrappers.scikit_learn.KerasRegressor):

	def __getstate__(self):
		state = self.__dict__
		if 'model' in state:
			model = state['model']
			model_hdf5_bio = io.BytesIO()
			with h5py.File(model_hdf5_bio, mode='w') as file:
				model.save(file)
			state['model'] = model_hdf5_bio
			state_copy = copy.deepcopy(state)
			state['model'] = model
			return state_copy
		else:
			return state

	def __setstate__(self, state):
		if 'model' in state:
			model_hdf5_bio = state['model']
			with h5py.File(model_hdf5_bio, mode='r') as file:
				state['model'] = keras.models.load_model(file)
		self.__dict__ = state

	def predict(self, x):
		return np.squeeze(self.model(x))



class KerasRegressorWithIntervals(KerasRegressor):

	def inverse_tau(self, N, lmbda=1e-5, p_dropout=0.1, ls_2=0.005):
		return (2 * N * lmbda) / (1 - p_dropout) / ls_2

	def fit(self, X, y):
		# fit neural network
		history = super(KerasRegressorWithIntervals, self).fit(X, y)

		# save training set size for tau adjustment
		self.n_train_samples = X.shape[0]

		return history

	def predict(self, X, n_preds=10):
		# compute several predictions for each sample
		y_preds = np.array([super(KerasRegressorWithIntervals, self).predict(X) for _ in range(n_preds)])

		# compute tau adjustment
		tau_inv = self.inverse_tau(self.n_train_samples)

		# compute mean and variance
		y_bar = np.mean(y_preds, axis=0)
		y_std = np.std(y_preds, axis=0) + tau_inv

		return y_bar, y_std



class RandomForestRegressorWithIntervals(sklearn.ensemble.RandomForestRegressor):

	def fit(self, X, y):
		# fit random forest
		super(RandomForestRegressorWithIntervals, self).fit(X, y)

		# save training set for variance estimate
		self.X_train = X

		return self

	def predict(self, X):
		# compute predictions
		y_bar = super(RandomForestRegressorWithIntervals, self).predict(X)

		# compute variance estimate
		y_var = forestci.random_forest_error(self, self.X_train, X)
		y_std = np.sqrt(y_var)

		return y_bar, y_std



def select_rows_by_values(df, column, values):
	return pd.concat([df[df[column].astype(str) == v] for v in values])



def is_categorical(df, column):
	return column != None and df[column].dtype.kind in 'OSUV'



def create_dataset(df, inputs, target=None):
	# extract input/target data from trace data
	X = df[inputs]
	y = df[target].values if target != None else None

	# one-hot encode categorical inputs, save categories
	options = {column: None for column in inputs}

	for column in inputs:
		if is_categorical(X, column):
			options[column] = X[column].unique().tolist()
			X = pd.get_dummies(X, columns=[column], drop_first=False)

	# save column order
	columns = list(X.columns)

	return X.values, y, columns, options



def create_dummy():
	return sklearn.dummy.DummyRegressor(strategy='quantile', quantile=1.0)



def create_mlp(
	input_shape,
	hidden_layer_sizes=[],
	activation='relu',
	activation_target=None,
	l1=0,
	l2=1e-5,
	p_dropout=0.1,
	intervals=False,
	optimizer='adam', # lr=0.001
	loss='mean_absolute_error',
	epochs=200):

	def build_fn():
		# create a 3-layer neural network
		x_input = keras.Input(shape=input_shape)

		x = x_input
		for units in hidden_layer_sizes:
			x = keras.layers.Dense(
				units=units,
				activation=activation,
				kernel_regularizer=keras.regularizers.l1_l2(l1, l2),
				bias_regularizer=keras.regularizers.l1_l2(l1, l2)
			)(x)

			if p_dropout != None:
				training = True if intervals else None
				x = keras.layers.Dropout(p_dropout)(x, training=training)

		y_output = keras.layers.Dense(units=1, activation=activation_target)(x)

		mlp = keras.models.Model(x_input, y_output)

		# compile the model
		mlp.compile(optimizer=optimizer, loss=loss)

		return mlp

	if intervals:
		Regressor = KerasRegressorWithIntervals
	else:
		Regressor = KerasRegressor

	return Regressor(
		build_fn=build_fn,
		batch_size=32,
		epochs=epochs,
		verbose=False,
		validation_split=0.1
	)



def create_rf(criterion='mae', intervals=False):
	if intervals:
		Regressor = RandomForestRegressorWithIntervals
	else:
		Regressor = sklearn.ensemble.RandomForestRegressor

	return Regressor(n_estimators=100, criterion=criterion)



def create_pipeline(reg, scaler_fn=sklearn.preprocessing.MaxAbsScaler):
	return sklearn.pipeline.Pipeline([
		('scaler', scaler_fn()),
		('reg', reg)
	])



def mean_absolute_percentage_error(y_true, y_pred):
	y_true = np.array(y_true)
	y_pred = np.array(y_pred)
	return 100 * np.mean(np.abs((y_true - y_pred) / y_true))



def prediction_interval_coverage(y_true, y_lower, y_upper):
	return 100 * np.mean((y_lower <= y_true) & (y_true <= y_upper))



def evaluate_cv(model, X, y, cv=5, ci=0.95):
	# initialize prediction arrays
	y_bar = np.empty_like(y)
	y_std = np.empty_like(y)

	# perform k-fold cross validation
	kfold = sklearn.model_selection.KFold(n_splits=cv, shuffle=True)

	for train_index, test_index in kfold.split(X):
		# reset session (for keras models)
		keras.backend.clear_session()

		# extract train/test split
		X_train, X_test = X[train_index], X[test_index]
		y_train, y_test = y[train_index], y[test_index]

		# train model
		model_ = sklearn.base.clone(model)
		model_.fit(X_train, y_train)

		# get model predictions
		y_bar_i, y_std_i = check_std(model_.predict(X_test))

		y_bar[test_index] = y_bar_i
		y_std[test_index] = y_std_i

	# compute prediction intervals
	y_lower, y_upper = predict_intervals(y_bar, y_std, ci=ci)

	# evaluate predictions
	scores = {
		'mpe': mean_absolute_percentage_error(y, y_bar),
		'cov': prediction_interval_coverage(y, y_lower, y_upper)
	}

	return scores, y_bar, y_std



def train(df, args):
	defaults = {
		'selectors': [],
		'min_std': 0.1,
		'scaler': 'maxabs',
		'model_type': 'mlp',
		'hidden_layer_sizes': [128, 128, 128],
		'epochs': 200,
		'intervals': True
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
		X, y, columns, options = create_dataset(df, args['inputs'], args['target'])
	except:
		raise RuntimeError('error: one or more input/output variables are not in the dataset')

	# select scaler
	try:
		scalers = {
			'maxabs': sklearn.preprocessing.MaxAbsScaler,
			'minmax': sklearn.preprocessing.MinMaxScaler,
			'standard': sklearn.preprocessing.StandardScaler
		}
		Scaler = scalers[args['scaler']]
	except:
		raise RuntimeError('error: scaler %s not recognized' % (args['scaler']))

	# use dummy regressor if target data has low variance
	if y.std() < args['min_std']:
		print('target value has low variance, using max value rounded up')
		model_type = 'dummy'
	else:
		model_type = args['model_type']

	# create regressor
	if model_type == 'dummy':
		reg = create_dummy()

	elif model_type == 'mlp':
		reg = create_mlp(
			X.shape[1],
			hidden_layer_sizes=args['hidden_layer_sizes'],
			epochs=args['epochs'],
			intervals=args['intervals'])

	elif model_type == 'rf':
		reg = create_rf(intervals=args['intervals'])

	# create model
	model = create_pipeline(reg, scaler_fn=Scaler)

	# save order of input columns
	args['inputs'] = options
	args['columns'] = columns

	# train and evaluate model
	scores, _, _ = evaluate_cv(model, X, y)

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
	y_bar, y_std = check_std(model.predict(X))

	return {
		'y_true': y,
		'y_pred': y_bar,
		'mpe': scores['mpe'],
		'cov': scores['cov']
	}



def predict(model_name, inputs, ci=0.95):
	# load model
	f = open('%s/%s.pkl' % (env.MODELS_DIR, model_name), 'rb')
	model = pickle.load(f)

	# load model configuration
	f = open('%s/%s.json' % (env.MODELS_DIR, model_name), 'r')
	args = json.load(f)

	# convert inputs into an ordered vector
	x_input = {}

	for column, options in args['inputs'].items():
		# one-hot encode categorical inputs
		if options != None:
			for v in options:
				x_input['%s_%s' % (column, v)] = (inputs[column] == v)

		# copy numerical inputs directly
		else:
			x_input[column] = inputs[column]

	x_input = [float(x_input[c]) for c in args['columns']]

	# perform inference
	X = np.array([x_input])
	y_bar, y_std = check_std(model.predict(X))
	y_lower, y_upper = predict_intervals(y_bar, y_std, ci=ci)

	# return results
	return {
		args['target']: [float(y_lower), float(y_bar), float(y_upper)]
	}