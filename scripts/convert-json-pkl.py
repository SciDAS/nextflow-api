#!/usr/bin/env python3

import argparse
import json
import pickle



def main():
	# parse command-line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('infile', help='input file')
	parser.add_argument('outfile', help='output file')

	args = parser.parse_args()

	# load input file
	infile = open(args.infile, 'r')
	obj = json.load(infile)

	# save output file
	outfile = open(args.outfile, 'wb')
	pickle.dump(obj, outfile)



if __name__ == '__main__':
	main()