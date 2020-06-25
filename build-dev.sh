#!/bin/bash

set -ex

USER='hellej'

DOCKER_IMAGE=${USER}/hope-green-path-server

docker build -t ${DOCKER_IMAGE}:dev -t ${DOCKER_IMAGE}:latest .

for TAG in dev latest; do
  docker push ${DOCKER_IMAGE}:${TAG}
done