FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NXF_VER="19.10.0"
EXPOSE 8080
EXPOSE 27017

# install package dependencies
RUN apt-get update -qq \
	&& apt-get install -qq -y apt-transport-https apt-utils ca-certificates curl git openjdk-8-jre python3.7 python3-pip cron mongodb

# install kubectl
RUN apt-get update && apt-get install -y apt-transport-https \
    && curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update \
    && apt-get install -y kubectl

# install nextflow
RUN curl -s https://get.nextflow.io | bash \
	&& mv nextflow /usr/local/bin \
	&& nextflow info

# Upgrade python3

RUN rm /usr/bin/python3 && ln -s python3.7 /usr/bin/python3

# install nextflow-api
WORKDIR /opt

ADD https://api.github.com/repos/scidas/nextflow-api/git/refs/heads/master version.json
RUN git clone -q https://github.com/scidas/nextflow-api.git

# move to nextflow-api directory
WORKDIR /opt/nextflow-api

# Switch to rodeo tag
RUN git fetch && git checkout origin/relative3

# install python dependencies
RUN pip3 install -r requirements.txt
RUN python3 --version
