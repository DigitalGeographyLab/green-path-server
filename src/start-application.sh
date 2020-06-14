#!/bin/bash

if [[ -z "${WORKER_COUNT}" || "${WORKER_COUNT}" = "1" ]]; then
  echo "Starting green path server with only 1 worker (default/dev)"
  gunicorn --workers=1 --bind=0.0.0.0:5000 --log-level=info --timeout 160 green_paths_app:app
else
  echo "Starting green path server with ${WORKER_COUNT} workers (prod)"
  gunicorn --workers=${WORKER_COUNT} --bind=0.0.0.0:5000 --log-level=warning --timeout 160 green_paths_app:app
fi