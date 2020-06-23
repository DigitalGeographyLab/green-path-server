#!/bin/bash

set -ex

RELEASE_TAG=${1}
USER='hellej'

if [[ -z "${RELEASE_TAG}" ]]; then
  echo "Add tag as argument (e.g. 1.0)"
  exit 1
fi

echo "Building images with tags 1 & ${RELEASE_TAG}"

for TAG in 1 ${RELEASE_TAG}; do
  DOCKER_IMAGE=${USER}/hope-green-path-server:${TAG}

  docker build -t ${DOCKER_IMAGE} .
  docker push ${DOCKER_IMAGE}
done