import logging
import os
import time
import traceback
from aqi_updater.aqi_fetcher import AqiFetcher
from aqi_updater.aqi_updater import AqiUpdater
import aqi_updater.configuration
import common.igraph as ig_utils


log = logging.getLogger('main')

graph_subset = eval(os.getenv('GRAPH_SUBSET', 'False'))
graph = ig_utils.read_graphml('graphs/kumpula.graphml' if graph_subset else 'graphs/hma.graphml')

aqi_fetcher = AqiFetcher('aqi_cache/')
aqi_updater = AqiUpdater(graph, 'aqi_cache/', 'aqi_updates/')


def fetch_process_aqi_data():
    try:
        aqi_fetcher.fetch_process_current_aqi_data()
        log.info('AQI fetch & processing succeeded')
    except Exception:
        log.error(traceback.format_exc())
        log.error(f'Failed to process AQI data to {aqi_fetcher.wip_aqi_tif}, retrying in 30s')
        time.sleep(30)
    finally:
        aqi_fetcher.finish_aqi_fetch()


def create_aqi_update_csv():
    try:
        aqi_updater.create_aqi_update_csv(aqi_fetcher.latest_aqi_tif)
        log.info('AQI update succeeded')
    except Exception:
        log.error(traceback.format_exc())
        log.error(f'Failed to update AQI from {aqi_fetcher.latest_aqi_tif}, retrying in 30s')
        time.sleep(30)
    finally:
        aqi_updater.finish_aqi_update()


if __name__ == '__main__':
    log.info('Starting AQI updater app')

    while True:
        if aqi_fetcher.new_aqi_available():
            fetch_process_aqi_data()
        if aqi_updater.new_update_available(aqi_fetcher.latest_aqi_tif):
            create_aqi_update_csv()
        time.sleep(10)
