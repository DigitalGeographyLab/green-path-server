#!/bin/bash

set -ex

USER='hellej'

for TAG in latest dev; do
  DOCKER_IMAGE=${USER}/hope-green-path-server:${TAG}

  docker build -t ${DOCKER_IMAGE} .
  docker push ${DOCKER_IMAGE}
done