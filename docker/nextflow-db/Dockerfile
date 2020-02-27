FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
EXPOSE 27017

# install package dependencies
RUN apt-get update -qq \
	&& apt-get install -qq -y git mongodb

# install nextflow-api
WORKDIR /opt

ADD https://api.github.com/repos/scidas/nextflow-api/git/refs/heads/master version.json
RUN git clone -q https://github.com/scidas/nextflow-api.git

# move to nextflow-api directory
WORKDIR /opt/nextflow-api
