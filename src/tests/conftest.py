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
def initial_client():
    patch_env_test_mode = patch('env.test_mode', True)
    patch_env_graph_file = patch('env.graph_file', r'graphs/kumpula.graphml')
    
    patch_noise_sens = patch('utils.noise_exposures.get_noise_sensitivities', return_value=__noise_sensitivities)
    patch_aq_sens = patch('utils.aq_exposures.get_aq_sensitivities', return_value=__aq_sensitivities)
    
    with patch_env_test_mode, patch_env_graph_file, patch_noise_sens, patch_aq_sens:
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
        if not data.get('aqi_data_updated', None):
            time.sleep(1)
            continue
        response = initial_client.get('/aqi-map-data-status')
        assert response.status_code == 200
        status = json.loads(response.data)
        if not status.get('aqi_map_data_available', None):
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
def test_exposure_prop_types() -> Callable[[dict, Union[float, None]], None]:
    def test_func(
        exp_dict: Dict[str, Union[int, float]], 
        expected_sum: Union[float, None] = None
    ):
        assert isinstance(exp_dict, dict)
        for key, val in exp_dict.items():
            num_key = int(key)
            assert isinstance(num_key, int)
            assert isinstance(val, (float, int))
        if expected_sum:
            val_sum = sum(exp_dict.values())
            diff = val_sum - expected_sum
            assert abs(diff) <= 0.11
    return test_func
