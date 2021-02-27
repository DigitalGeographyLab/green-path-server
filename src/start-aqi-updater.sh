#!/bin/bash

if [[ ! -z "${GRAPH_SUBSET}" && "${GRAPH_SUBSET}" = "True" ]]; then
  echo "Starting AQI updater with graph subset"
else
  echo "Starting AQI updater with full graph"
fi

python -u aqi_updater_main.py
