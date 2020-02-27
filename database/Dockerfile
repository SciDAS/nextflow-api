FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NXF_VER="19.10.0"
EXPOSE 27017

# install package dependencies
RUN apt-get update -qq \
	&& apt-get install -qq -y apt-transport-https apt-utils ca-certificates curl git mongodb openjdk-8-jre python3 python3-pip

# install kubectl
RUN apt-get update && apt-get install -y apt-transport-https \
    && curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update \
    && apt-get install -y kubectl

RUN mkdir -p /scripts
ADD scripts/* /scripts/
