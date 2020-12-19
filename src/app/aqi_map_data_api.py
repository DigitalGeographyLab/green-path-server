from typing import List, Dict, Union, Callable
from dataclasses import dataclass
import os
import env
import random
from functools import partial
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from app.logger import Logger


@dataclass(frozen=True)
class AqiMapDataApi:
    start: Callable
    get_data: Callable
    get_status: Callable


@dataclass(frozen=False)
class AqiMapDataState:
    latest_aqi_data_name: str = ''
    latest_aqi_map_data: str = '' # {"data":[[0,3],[1,3],[2,3],...]}
    latest_aqi_map_data_utc_time_secs: str = None


def __get_expected_aqi_data_name() -> str:
    """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
    """
    if env.test_mode:
        return 'aqi_2020-10-25T14.csv'
    curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
    return 'aqi_'+ curdt +'.csv'


def __get_aqi_data_utc_time_secs(log: Logger, aqi_data_name: str) -> Union[int, None]:
    try:
        aqi_data_time = aqi_data_name.split('aqi_', 1)[1].split('.')[0]
        dt = datetime.strptime(aqi_data_time, '%Y-%m-%dT%H')
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        log.error(f'Could not parse UTC time from {aqi_data_name}')
        return None


def __aqi_data_available(expected_aqi_data_name: str, aqi_dir: str) -> bool:
    """Returns true if new AQI update file is both expected and available, else returns False.
    """
    return os.path.exists(aqi_dir + expected_aqi_data_name) and os.path.exists(aqi_dir + 'aqi_map.json')


def __update_state(log: Logger, f, new_aqi_data_name: str, state: AqiMapDataState) -> None:
    state.latest_aqi_map_data = f.read()
    state.latest_aqi_data_name = new_aqi_data_name
    state.latest_aqi_map_data_utc_time_secs = __get_aqi_data_utc_time_secs(log, new_aqi_data_name)


def __maybe_load_updated_aqi_data(log: Logger, aqi_dir: str, state: AqiMapDataState) -> Union[None, str]:
    expected_aqi_data_name = __get_expected_aqi_data_name()

    if state.latest_aqi_data_name != expected_aqi_data_name:
        if __aqi_data_available(expected_aqi_data_name, aqi_dir):
            try:
                with open(aqi_dir + 'aqi_map.json', 'r') as f:
                    __update_state(log, f, expected_aqi_data_name, state)
                    log.info(f'Loaded new AQI data for map API')
            except Exception:
                log.error(f'Could not load new AQI data for map API from "{expected_aqi_data_name}"')


def __start_aqi_map_data_api(log: Logger, aqi_data_loader: Callable):
    check_interval = 5 + random.randint(1, 10)

    log.info(f'Starting AQI map data API with {check_interval} s check interval')
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        aqi_data_loader,
        'interval',
        seconds=5,
        max_instances=1,
        next_run_time=datetime.now()
    )
    scheduler.start()


def __get_aqi_map_data(log: Logger, state: AqiMapDataState):
    return state.latest_aqi_map_data


def __get_aqi_map_data_status(state: AqiMapDataState):
    return {
        'aqi_map_data_available': state.latest_aqi_map_data != '',
        'aqi_map_data_utc_time_secs': state.latest_aqi_map_data_utc_time_secs
    }


def get_aqi_map_data_api(log: Logger, aqi_dir: str='aqi_updates/') -> AqiMapDataApi:
    use_aqi_dir = aqi_dir if not env.test_mode else 'aqi_updates/test_data/'
    
    state = AqiMapDataState()
    aqi_data_loader = partial(__maybe_load_updated_aqi_data, log, use_aqi_dir, state)
    start = partial(__start_aqi_map_data_api, log, aqi_data_loader)
    get_aqi_map_data = partial(__get_aqi_map_data, log, state)
    get_aqi_map_data_status = partial(__get_aqi_map_data_status, state)
    return AqiMapDataApi(start, get_aqi_map_data, get_aqi_map_data_status)
