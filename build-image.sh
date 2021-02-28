#!/bin/bash
set -ex

USER='hellej'

PS3='Select project: '
option_labels=("green paths server" "graph updater")
select opt in "${option_labels[@]}"; do
  case $opt in
  "green paths server")
    echo "green paths server"
    DOCKER_SUFFIX='.gp-server'
    DOCKER_IMAGE=${USER}/hope-green-path-server
    break
    ;;
  "graph updater")
    echo "aqi updater"
    DOCKER_SUFFIX='.aqi-updater'
    DOCKER_IMAGE=${USER}/hope-graph-updater
    break
    ;;
  *)
    break
    ;;
  esac
done

if [[ -z "${DOCKER_SUFFIX}" ]]; then
  echo "Invalid option -> cancel build."
  exit 0
fi

echo "Building image from: Dockerfile${DOCKER_SUFFIX}"

PS3='Select image to build: '
option_labels=("dev" "prod" "all")
select opt in "${option_labels[@]}"; do
  case $opt in
  "dev")
    WHICH_IMAGE='dev'
    echo "Build dev"
    break
    ;;
  "prod")
    WHICH_IMAGE='prod'
    echo "Build prod"
    break
    ;;
  "all")
    WHICH_IMAGE='all'
    echo "Build all"
    break
    ;;
  *)
    break
    ;;
  esac
done

if [[ -z "${WHICH_IMAGE}" ]]; then
  echo "Invalid option -> cancel build."
  exit 0
fi

echo "Build image (latest)"
docker build -f Dockerfile${DOCKER_SUFFIX} -t ${DOCKER_IMAGE}:latest .

if [[ $WHICH_IMAGE == "dev" || $WHICH_IMAGE == "all" ]] ; then
  echo "Tag & push dev"
  docker tag ${DOCKER_IMAGE}:latest ${DOCKER_IMAGE}:dev
  for TAG in latest dev; do
    docker push ${DOCKER_IMAGE}:${TAG}
  done
fi

if [[ $WHICH_IMAGE == "prod" || $WHICH_IMAGE == "all" ]] ; then
  echo "Tag & push prod (1)"
  docker tag ${DOCKER_IMAGE}:latest ${DOCKER_IMAGE}:1
  for TAG in latest 1; do
    docker push ${DOCKER_IMAGE}:${TAG}
  done
fi
