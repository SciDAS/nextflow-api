FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NXF_VER="21.04.3"
EXPOSE 8080
EXPOSE 27017

# install package dependencies
RUN apt-get update -qq \
	&& apt-get install -qq -y \
		apt-transport-https \
		apt-utils \
		ca-certificates \
		cron \
		curl \
		git \
		mongodb \
		openjdk-8-jre \
		python3.7 \
		python3-pip \
		zip

# change python to refer to python 3.7
RUN rm /usr/bin/python3 && ln -s python3.7 /usr/bin/python3

# install kubectl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
	&& echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list \
	&& apt-get update -qq \
	&& apt-get install -qq -y kubectl

# install nextflow
RUN curl -s https://get.nextflow.io | bash \
	&& mv nextflow /usr/local/bin \
	&& nextflow info

# install nextflow-api from build context
WORKDIR /opt/nextflow-api

COPY . .

# install python dependencies
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt
