#!/bin/bash

set -ex

RELEASE_TAG=${1}
USER='hellej'

DOCKER_IMAGE=${USER}/hope-green-path-server

if [[ -z "${RELEASE_TAG}" ]]; then
  echo "Building image with tag 1"
  docker build -t ${DOCKER_IMAGE}:1 .
  docker push ${DOCKER_IMAGE}:1
  exit 0
fi

echo "Building images with tags 1 & ${RELEASE_TAG}"
docker build -t ${DOCKER_IMAGE}:1 -t ${DOCKER_IMAGE}:${RELEASE_TAG} .

for TAG in 1 ${RELEASE_TAG}; do
  docker push ${DOCKER_IMAGE}:${TAG}
done