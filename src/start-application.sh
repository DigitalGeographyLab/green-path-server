#!/bin/bash

if [[ -z "${LOG_LEVEL}" ]]; then
  export LOG_LEVEL="info"
fi

if [[ -z "${WORKER_COUNT}" ]]; then
  export WORKER_COUNT="1"
fi

if [[ ! -z "${RUN_DEV}" && "${RUN_DEV}" = "True" ]]; then
  echo "Starting green path server (dev) with ${WORKER_COUNT} workers and small graph"
  export GRAPH_SUBSET="True"
  export LOG_LEVEL="info"
  gunicorn --workers=${WORKER_COUNT} --bind=0.0.0.0:5000 --log-level=${LOG_LEVEL} --timeout 450 green_paths_app:app
else
  echo "Starting green path server (prod) with ${WORKER_COUNT} workers"
  gunicorn --workers=${WORKER_COUNT} --bind=0.0.0.0:5000 --log-level=${LOG_LEVEL} --timeout 450 green_paths_app:app
fi