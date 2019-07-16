FROM ubuntu:18.04

EXPOSE 8080

# install dependencies
RUN apt-get -qq update \
	&& apt-get -qq install -y curl default-jdk git python3 python3-pip

# gcloud (required for GKE)

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get install -y apt-transport-https ca-certificates apt-utils \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update -y && apt-get install -y google-cloud-sdk

# install nextflow
RUN curl -s https://get.nextflow.io | bash \
	&& mv nextflow /usr/local/bin

# install nextflow-gke server
WORKDIR /opt

RUN git clone https://github.com/SciDAS/nextflow-gke.git

# install python dependencies
RUN pip3 install -r nextflow-gke/requirements.txt

# move to nextflow-gke directory
WORKDIR /opt/nextflow-gke
