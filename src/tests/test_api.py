
from typing import Dict, Union, Tuple, Callable
from unittest.mock import patch, MagicMock
from shapely.geometry import LineString
from utils.geometry import project_geom
import os
import json
import pytest
import time
import json


@pytest.fixture
def set_test_env(monkeypatch):
    monkeypatch.setenv('GRAPH_SUBSET', 'True')


@pytest.fixture
def client(set_test_env):
    mock = MagicMock(return_value=[ 0.1, 0.4, 1.3, 3.5, 6 ])
    with patch('utils.noise_exposures.get_noise_sensitivities', mock):
        from green_paths_app import app
        with app.test_client() as client:
            yield client


def test_env(set_test_env):
    assert os.getenv('GRAPH_SUBSET') == 'True'


def test_endpoint(client):
    response = client.get('/')
    response.get_data().decode('utf-8') == 'Keep calm and walk green paths.'
    assert response.status_code == 200


def test_aqi_status_path(client):
    response = client.get('/aqistatus')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['aqi_data_updated'] == False
    assert data['aqi_data_utc_time_secs'] == None


def test_aqi_map_data_status_path(client):
    response = client.get('/aqi-map-data-status')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert status['aqi_map_data_available'] == False
    assert status['aqi_map_data_utc_time_secs'] == None


def test_aqi_map_data_path(client):
    response = client.get('/aqi-map-data')
    assert response.status_code == 200
    # before first AQI map data load it should return just empty string
    assert response.get_data().decode('utf-8') == ''


def test_clean_paths_unavailable(client):
    response = client.get('/paths/walk/clean/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    # before first AQI map data load it should return just empty string
    data = json.loads(response.data)
    assert data['error_key'] == 'no_real_time_aqi_available'


@pytest.fixture
def quiet_path_set_1(client) -> dict:
    response = client.get('/paths/walk/quiet/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) > 1
    assert len(data['edge_FC']['features']) > 20
    yield data


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


@pytest.fixture
def test_short_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        assert props['id'] == 'short'
        assert isinstance(props['len_diff'], (float, int))
        assert props['len_diff_rat'] is None
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['length_b'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert props['mdB_diff'] is None
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['nei'], (float, int))
        assert props['nei_diff'] is None
        assert props['nei_diff_rat'] is None
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'])
        test_exposure_prop_types(props['noise_range_exps'])
        test_exposure_prop_types(props['noises'])
        assert props['path_score'] is None
        assert isinstance(props['type'], str)
        assert props['type'] == 'short'
    return test_func


@pytest.fixture
def test_quiet_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        assert isinstance(props['len_diff'], (float, int))
        assert isinstance(props['len_diff_rat'], (float, int))
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['length_b'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert isinstance(props['mdB_diff'], (float, int))
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['nei'], (float, int))
        assert isinstance(props['nei_diff'], (float, int))
        assert isinstance(props['nei_diff_rat'], (float, int))
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'])
        test_exposure_prop_types(props['noise_range_exps'])
        test_exposure_prop_types(props['noises'])
        assert isinstance(props['path_score'], (float, int))
        assert isinstance(props['type'], str)
        assert props['type'] == 'quiet'
    return test_func


def test_quiet_paths_1_shortest_path_prop_types(
    quiet_path_set_1, 
    test_line_geometry, 
    test_short_path_prop_types
):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    s_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'short']
    assert len(s_paths) == 1
    s_path = s_paths[0]
    props = s_path['properties']
    test_line_geometry(s_path['geometry'])
    test_short_path_prop_types(props)


def test_quiet_paths_1_quiet_path_prop_types(
    quiet_path_set_1, 
    test_line_geometry,
    test_quiet_path_prop_types
):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    q_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'quiet']
    assert len(q_paths) == 3
    for qp in q_paths:
        test_line_geometry(qp['geometry'])
        test_quiet_path_prop_types(qp['properties'])


def test_quiet_paths_1_shortest_path_geom(quiet_path_set_1):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    s_path = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'short'][0]
    geom = s_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1340.0


def test_quiet_paths_1_shortest_path_props(quiet_path_set_1):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    s_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'short']
    assert len(s_paths) == 1
    s_path = s_paths[0]
    props = s_path['properties']
    assert props['cost_coeff'] == 0
    assert props['id'] == 'short'
    assert props['len_diff'] == 0
    assert props['len_diff_rat'] == None
    assert props['length'] == 1340.04
    assert props['length_b'] == 1373.42
    assert props['mdB'] == 73.8
    assert props['mdB_diff'] == None
    assert props['missing_aqi'] == True
    assert props['missing_noises'] == False
    assert props['nei'] == 1955.2
    assert props['nei_diff'] == None
    assert props['nei_diff_rat'] == None # used in UI
    assert props['nei_norm'] == 0.62 # used in UI
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"55": 0.7, "60": 12.0, "65": 4.5, "70": 82.9}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"55": 9.01, "60": 160.5, "65": 60.3, "70": 1110.23}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"55": 9.01, "60": 160.5, "65": 60.3, "70": 342.65, "75": 767.58}'
    assert props['path_score'] is None
    assert props['type'] == 'short'


def test_quiet_paths_1_quiet_path_geom(quiet_path_set_1):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    q_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == 'q_1.3'][0]
    geom = q_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1475.14


def test_quiet_paths_1_quiet_path_props(quiet_path_set_1):
    data = quiet_path_set_1
    path_fc = data['path_FC']
    q_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == 'q_1.3'][0]
    props = q_path['properties']
    assert props['cost_coeff'] == 1.3
    assert props['id'] == "q_1.3"
    assert props['len_diff'] == 135.1
    assert props['len_diff_rat'] == 10.1
    assert props['length'] == 1475.16
    assert props['length_b'] == 1954.72
    assert props['mdB'] == 55.1
    assert props['mdB_diff'] == -18.7
    assert props['missing_aqi'] == True
    assert props['missing_noises'] == False
    assert props['nei'] == 603.4
    assert props['nei_diff'] == -1351.8
    assert props['nei_diff_rat'] == -69.1
    assert props['nei_norm'] == 0.17
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"40": 29.0, "50": 16.1, "55": 26.3, "60": 28.4, "65": 0.2}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"40": 428.52, "50": 237.59, "55": 387.69, "60": 418.35, "65": 3.01}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"40": 33.96, "45": 394.56, "50": 237.59, "55": 387.69, "60": 418.35, "65": 3.01}'
    assert props['path_score'] == 10.0
    assert props['type'] == 'quiet'


@pytest.fixture
def test_edge_props() -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['p_len_diff'], (float, int)) # TODO remove property since not used in UI
        assert isinstance(props['p_length'], (float, int))
        assert isinstance(props['path'], str)
        assert isinstance(props['value'], (float, int))
        assert props['p_length'] > 0
        assert len(props['path']) > 0
        assert props['value'] > 0
    return test_func


def test_quiet_paths_1_edge_fc(
    quiet_path_set_1, 
    test_line_geometry, 
    test_edge_props
):
    data = quiet_path_set_1
    edge_fc = data['edge_FC']
    path_fc = data['path_FC']
    assert edge_fc['type'] == 'FeatureCollection'
    assert isinstance(edge_fc['features'], list)
    assert len(edge_fc['features']) == 37
    for feat in edge_fc['features']:
        assert feat['type'] == 'Feature'
        test_line_geometry(feat['geometry'])
        test_edge_props(feat['properties'])
    
    # test that same paths (ids) are present in both edge_FC and path_FC
    path_ids_in_edges = set([feat['properties']['path'] for feat in edge_fc['features']])
    assert len(path_ids_in_edges) == len(path_fc['features'])
    assert path_ids_in_edges == set([path['properties']['id'] for path in path_fc['features']])


@pytest.fixture
def quiet_paths_on_one_street(client) -> Tuple[dict]:
    """Returns paths with origin and destination on the same street."""
    response = client.get('/paths/walk/quiet/60.214233,24.971411/60.213558,24.970785')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert data['edge_FC']['type'] == 'FeatureCollection'
    yield (data['edge_FC'], data['path_FC'])


def test_quiet_paths_on_same_street(
    quiet_path_set_1,
    quiet_paths_on_one_street,
    test_line_geometry, 
    test_short_path_prop_types,
    test_edge_props
):
    """Tests that if origin and destination are on the same street, the resultsets are still as expected."""
    edge_fc, path_fc = quiet_paths_on_one_street
    # edges
    assert len(edge_fc['features']) == 1
    test_line_geometry(edge_fc['features'][0]['geometry'])
    test_edge_props(edge_fc['features'][0]['properties'])
    # paths
    assert len(path_fc['features']) == 1
    test_line_geometry(path_fc['features'][0]['geometry'])
    test_short_path_prop_types(path_fc['features'][0]['properties'])
