from typing import List, Dict, Union, Callable
from dataclasses import dataclass
import os
import random
from functools import partial
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.logger import Logger


@dataclass(frozen=True)
class AqiMapDataApi:
    start: Callable
    get_aqi_map_data: Callable


@dataclass(frozen=False)
class AqiMapDataState:
    latest_aqi_data_name: str = ''
    latest_aqi_map_data: str = '' # {"data":[[0,3],[1,3],[2,3],...]}


def __get_expected_aqi_data_name() -> str:
    """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
    """
    curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
    return 'aqi_'+ curdt +'.csv'


def __aqi_data_available(expected_aqi_data_name: str, aqi_dir: str) -> bool:
    """Returns true if new AQI update file is both expected and available, else returns False.
    """
    return os.path.exists(aqi_dir + expected_aqi_data_name) and os.path.exists(aqi_dir + 'aqi_map.json')


def __maybe_load_updated_aqi_data(log: Logger, aqi_dir: str, state: AqiMapDataState) -> Union[None, str]:
    expected_aqi_data_name = __get_expected_aqi_data_name()

    if state.latest_aqi_data_name != expected_aqi_data_name:
        if __aqi_data_available(expected_aqi_data_name, aqi_dir):
            with open(aqi_dir + 'aqi_map.json', 'r') as f:
                state.latest_aqi_map_data = f.read()
                state.latest_aqi_data_name = expected_aqi_data_name
                log.info(f'Loaded new AQI data for map API')


def __start_aqi_map_data_api(log: Logger, aqi_dir: str, state: AqiMapDataState):
    aqi_data_loader = partial(__maybe_load_updated_aqi_data, log, aqi_dir, state)
    check_interval = 5 + random.randint(1, 10)

    log.info(f'Starting AQI map data API with {check_interval} s check interval')
    scheduler = BackgroundScheduler()
    scheduler.add_job(aqi_data_loader, 'interval', seconds=check_interval, max_instances=2)
    scheduler.start()


def __get_aqi_map_data(log: Logger, state: AqiMapDataState):
    return state.latest_aqi_map_data


def get_aqi_map_data_api(log: Logger, aqi_dir: str='aqi_updates/') -> AqiMapDataApi:
    state = AqiMapDataState()
    start = partial(__start_aqi_map_data_api, log, aqi_dir, state)
    get_aqi_map_data = partial(__get_aqi_map_data, log, state)
    return AqiMapDataApi(start, get_aqi_map_data)
