#!/bin/bash

docker run --rm \
	--name jupyter-notebook \
	-p 8888:8888 \
	--user root \
	-e NB_UID=$UID \
	-e NB_GID=$(id -g $USER) \
	-v $(pwd)/work:/home/jovyan/work:rw \
	jupyter/scipy-notebook \
	start-notebook.sh
