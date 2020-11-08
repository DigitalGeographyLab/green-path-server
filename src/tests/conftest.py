from typing import Dict, Union, Tuple, Callable
from unittest.mock import patch
import pytest
import json
import time
from utils.geometry import project_geom
from shapely.geometry import LineString


__noise_sensitivities = [ 0.1, 0.4, 1.3, 3.5, 6 ]
__aq_sensitivities = [ 5, 15, 30 ]


@pytest.fixture(scope='module')
def monkeymodule():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='module')
def clean_path_test_env(monkeymodule):
    monkeymodule.setenv('GRAPH_SUBSET', 'True')
    monkeymodule.setenv('TEST_MODE', 'True')


@pytest.fixture(scope='module')
def initial_client(clean_path_test_env):
    with patch('utils.noise_exposures.get_noise_sensitivities', return_value=__noise_sensitivities):
        with patch('utils.aq_exposures.get_aq_sensitivities', return_value=__aq_sensitivities):
            from green_paths_app import app
            with app.test_client() as gp_client:
                yield gp_client


@pytest.fixture(scope='module')
def client(initial_client):
    """Returns API client only when it has loaded AQI data to the routing graph and for AQI map data API."""
    for _ in range(20):
        response = initial_client.get('/aqistatus')
        assert response.status_code == 200
        data = json.loads(response.data)
        if not data['aqi_data_updated']:
            time.sleep(1)
            continue
        response = initial_client.get('/aqi-map-data-status')
        assert response.status_code == 200
        status = json.loads(response.data)
        if not status['aqi_map_data_available']:
            time.sleep(1)
            continue
        break
    yield initial_client


@pytest.fixture
def test_line_geometry() -> Callable[[dict], None]:
    def test_func(geometry: dict):
        assert geometry['type'] == 'LineString'
        coords = geometry['coordinates']
        assert isinstance(coords, list)
        line = LineString(coords)
        assert isinstance(line, LineString)
        assert line.is_valid
        # test that the length is a positive number
        proj_line = project_geom(line)
        assert isinstance(proj_line.length, (float, int))
        assert proj_line.length >= 0.1
    return test_func


@pytest.fixture
def test_exposure_prop_types() -> Callable[[dict], None]:
    def test_func(exp_dict: Dict[str, Union[int, float]]):
        assert isinstance(exp_dict, dict)
        for key, val in exp_dict.items():
            num_key = int(key)
            assert isinstance(num_key, int)
            assert isinstance(val, (float, int))
    return test_func
