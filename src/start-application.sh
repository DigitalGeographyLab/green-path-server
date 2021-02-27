#!/bin/bash

if [[ -z "${LOG_LEVEL}" ]]; then
  export LOG_LEVEL="info"
fi

if [[ -z "${WORKER_COUNT}" ]]; then
  export WORKER_COUNT="1"
fi

echo "Starting green path server with ${WORKER_COUNT} workers and log level ${LOG_LEVEL}"
gunicorn --workers=${WORKER_COUNT} --bind=0.0.0.0:5000 --log-level=${LOG_LEVEL} --timeout 450 gp_server_main:app
