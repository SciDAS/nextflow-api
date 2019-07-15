FROM ubuntu:18.04

EXPOSE 8080

# install dependencies
RUN apt-get -qq update \
	&& apt-get -qq install -y curl default-jdk git python3 python3-pip

# install nextflow
RUN curl -s https://get.nextflow.io | bash \
	&& mv nextflow /usr/local/bin

# install nextflow-gke server
WORKDIR /opt

RUN git clone -q https://github.com/bentsherman/nextflow-gke.git

# install python dependencies
RUN pip3 install -r nextflow-gke/requirements.txt

# move to nextflow-gke directory
WORKDIR /opt/nextflow-gke
