import time
from unittest.mock import patch, MagicMock
import app.aqi_map_data_api as aqi_map_data_api
from app.logger import Logger


log = Logger()
aqi_dir = 'tests/aqi_cache/'


def test_initial_aqi_map_data_api():
    api = aqi_map_data_api.get_aqi_map_data_api(log, aqi_dir)
    api.start()
    status = api.get_status()
    assert status['aqi_map_data_available'] == False
    assert status['aqi_map_data_utc_time_secs'] == None


def test_aqi_map_data_api_after_update():
    mock = MagicMock(return_value='aqi_2019-11-08T14.csv')
    with patch('app.aqi_map_data_api.__get_expected_aqi_data_name', mock):
        api = aqi_map_data_api.get_aqi_map_data_api(log, aqi_dir)
        api.start()
        # check that the mock works
        assert aqi_map_data_api.__get_expected_aqi_data_name() == 'aqi_2019-11-08T14.csv'
        # wait before until AQI map data update is done
        time.sleep(5)
        status = api.get_status()
        assert status['aqi_map_data_available'] == True
        assert status['aqi_map_data_utc_time_secs'] == 1573221600
