import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns



def select_rows_by_values(df, column, values):
	return pd.concat([df[df[column].astype(str) == v] for v in values])



def is_continuous(df, column):
	return column != None and df[column].dtype.kind in 'biufcmM'



def is_discrete(df, column):
	return column != None and df[column].dtype.kind in 'OSUV'



def contingency_table(x, y, data, **kwargs):
	# compute indices for categorical variables
	x_values = sorted(list(set(x)))
	y_values = sorted(list(set(y)))
	x_idx = [x_values.index(x_i) for x_i in x]
	y_idx = [y_values.index(y_i) for y_i in y]

	# create contingency table
	ct = pd.DataFrame(
		np.zeros((len(y_values), len(x_values))),
		index=y_values,
		columns=x_values,
		dtype=np.int32)

	for x_i, y_i in zip(x_idx, y_idx):
		ct.iloc[y_i, x_i] += 1

	# plot contingency table
	sns.heatmap(ct, annot=True, fmt='d', cbar=False, square=True, **kwargs)



def visualize(data, args):
	defaults = {
		'plot_type': None,
		'yaxis': None,
		'row': None,
		'col': None,
		'hue': None,
		'selectors': [],
		'sharex': False,
		'sharey': False,
		'height': 3,
		'aspect': 1,
		'color': None,
		'palette': None,
		'xscale': None,
		'yscale': None,
		'rotate_xticklabels': False,
		'rotate_yticklabels': False
	}

	args = {**defaults, **args}

	# prepare axis columns in dataframe
	axes = [
		args['xaxis'],
		args['yaxis'],
		args['row'],
		args['col'],
		args['hue']
	]

	for column in axes:
		# skip columns which were not specified
		if column == None:
			continue

		# remove rows which have missing values in column
		data = data[~data[column].isna()]

	# apply selectorss to dataframe
	for selector in args['selectors']:
		# parse column and selected values
		column, values = selector.split('=')
		values = values.split(',')

		# select rows from dataframe
		if values != None and len(values) > 0:
			data = select_rows_by_values(data, column, values)

	if len(data.index) == 0:
		raise RuntimeError('error: no data to visualize')

	# sort data by row, col, and hue values
	if args['row'] != None:
		data.sort_values(by=args['row'], inplace=True, kind='mergesort')

	if args['col'] != None:
		data.sort_values(by=args['col'], inplace=True, kind='mergesort')

	if args['hue'] != None:
		data.sort_values(by=args['hue'], inplace=True, kind='mergesort')

	# create a facet grid for plotting
	g = sns.FacetGrid(
		data,
		row=args['row'],
		col=args['col'],
		sharex=args['sharex'],
		sharey=args['sharey'],
		height=args['height'],
		aspect=args['aspect'],
		margin_titles=True)

	# determine plot type if not specified
	if args['plot_type'] == None:
		# if x is continuous, use histogram
		if is_continuous(data, args['xaxis']) and args['yaxis'] == None:
			args['plot_type'] = 'hist'

		# if x is discrete, use count plot
		elif is_discrete(data, args['xaxis']) and args['yaxis'] == None:
			args['plot_type'] = 'count'

		# if x and y are continuous, use scatter plot
		elif is_continuous(data, args['xaxis']) and is_continuous(data, args['yaxis']):
			args['plot_type'] = 'scatter'

		# if x and y are discrete, use contingency table
		elif is_discrete(data, args['xaxis']) and is_discrete(data, args['yaxis']):
			args['plot_type'] = 'ct'

		# if x is discrete and y is continuous, use bar plot
		elif is_discrete(data, args['xaxis']) and is_continuous(data, args['yaxis']):
			args['plot_type'] = 'bar'

		# otherwise throw an error
		else:
			raise RuntimeError('error: could not find a plotting method for the given axes')

	# create order of x values for discrete plots
	# unless y-axis sorting is enabled (so as not to override it)
	if is_discrete(data, args['xaxis']):
		x_values = sorted(list(set(data[args['xaxis']])))
	else:
		x_values = None

	# create plot
	if args['plot_type'] == 'hist':
		g.map(
			sns.histplot,
			args['xaxis'],
			color=args['color'])

	elif args['plot_type'] == 'count':
		g.map(
			sns.countplot,
			args['xaxis'],
			hue=args['hue'],
			color=args['color'],
			palette=args['palette'])

	elif args['plot_type'] == 'scatter':
		g = g.map(
			sns.scatterplot,
			args['xaxis'],
			args['yaxis'],
			hue=args['hue'],
			data=data,
			color=args['color'])

		if args['hue'] != None:
			g.add_legend()

	elif args['plot_type'] == 'ct':
		g = g.map(
			contingency_table,
			args['xaxis'],
			args['yaxis'],
			data=data,
			color=args['color'])

	elif args['plot_type'] == 'bar':
		g = g.map(
			sns.barplot,
			args['xaxis'],
			args['yaxis'],
			hue=args['hue'],
			data=data,
			ci=68,
			color=args['color'],
			palette=args['palette'],
			order=x_values)

		if args['hue'] != None:
			g.add_legend()

	elif args['plot_type'] == 'point':
		g = g.map(
			sns.pointplot,
			args['xaxis'],
			args['yaxis'],
			hue=args['hue'],
			data=data,
			ci=68,
			capsize=0.1,
			color=args['color'],
			palette=args['palette'],
			markers='x',
			linestyles='--',
			order=x_values)

		if args['hue'] != None:
			g.add_legend()

	# set x-axis scale if specified
	if args['xscale'] != None:
		g.set(xscale=args['xscale'])

	# set y-axis scale if specified
	if args['yscale'] != None:
		g.set(yscale=args['yscale'])

	# rotate x-axis tick labels if specified
	if args['rotate_xticklabels']:
		plt.xticks(rotation=45)

	# rotate y-axis tick labels if specified
	if args['rotate_yticklabels']:
		plt.yticks(rotation=45)

	# disable x-axis ticks if there are too many categories
	if is_discrete(data, args['xaxis']) and len(set(data[args['xaxis']])) >= 100:
		plt.xticks([])

	# save output figure
	outfile = '/tmp/%s.png' % (args['plot_name'])
	plt.savefig(outfile)
	plt.close()

	return outfile