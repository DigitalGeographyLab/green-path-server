#!/bin/bash

set -ex

RELEASE_TAG=${1}

sh ./build-dev.sh
sh ./build-prod.sh ${RELEASE_TAG}