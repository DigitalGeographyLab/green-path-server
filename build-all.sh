#!/bin/bash

set -ex

RELEASE_TAG=${1}

if [[ -z "${RELEASE_TAG}" ]]; then
  echo "Add tag as argument (e.g. 1.0)"
  exit 1
fi

sh ./build-dev.sh
sh ./build-prod.sh ${RELEASE_TAG}