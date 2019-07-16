#!/bin/bash
# Collect output data into a single archive.

# parse command-line arguments
if [[ $# != 2 ]]; then
	echo "usage: $0 <id> <path>"
	exit -1
fi

ID="$1"
SRC_PATH="$2"
DST_DIRNAME="$(dirname ${SRC_PATH})"
DST_BASENAME="${ID}-$(basename ${SRC_PATH}).tar.gz"

# replace any links with the original files
for f in $(find ${SRC_PATH} -type l); do
	cp --remove-destination $(readlink $f) $f
done

# create archive of output data
cd ${DST_DIRNAME}

tar -czf ${DST_BASENAME} $(basename ${SRC_PATH})/*
