#!/bin/bash

set -ex

USER='hellej'

DOCKER_IMAGE=${USER}/hope-green-path-server:dev
DOCKER_IMAGE_LATEST=${USER}/hope-green-path-server:latest

docker build -t ${DOCKER_IMAGE} .

docker tag ${DOCKER_IMAGE} ${DOCKER_IMAGE_LATEST}
docker login
docker push ${DOCKER_IMAGE_LATEST}
