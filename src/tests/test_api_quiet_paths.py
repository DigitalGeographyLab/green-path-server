from typing import Dict, Union, Tuple, Callable
from shapely.geometry import LineString
from utils.geometry import project_geom
from app.constants import cost_prefix_dict, TravelMode, RoutingMode
import json
import pytest


@pytest.fixture
def path_set_1(client) -> dict:
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
def test_short_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        test_exposure_prop_types(props['gvi_cl_exps'])
        test_exposure_prop_types(props['gvi_cl_pcts'], 100.0)
        assert isinstance(props['gvi_m'], (float, int))
        assert props['gvi_m_diff'] is None
        assert props['id'] == 'short'
        assert isinstance(props['len_diff'], (float, int))
        assert props['len_diff_rat'] is None
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['length_b'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert props['mdB_diff'] is None
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['missing_gvi'], bool)
        assert isinstance(props['nei'], (float, int))
        assert props['nei_diff'] is None
        assert props['nei_diff_rat'] is None
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'], 100.0)
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
        test_exposure_prop_types(props['gvi_cl_exps'])
        test_exposure_prop_types(props['gvi_cl_pcts'], 100.0)
        assert isinstance(props['gvi_m'], (float, int))
        assert isinstance(props['gvi_m_diff'], (float, int))
        assert isinstance(props['id'], str)
        assert isinstance(props['len_diff'], (float, int))
        assert isinstance(props['len_diff_rat'], (float, int))
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['length_b'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert isinstance(props['mdB_diff'], (float, int))
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['missing_gvi'], bool)
        assert isinstance(props['nei'], (float, int))
        assert isinstance(props['nei_diff'], (float, int))
        assert isinstance(props['nei_diff_rat'], (float, int))
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'], 100.0)
        test_exposure_prop_types(props['noise_range_exps'])
        test_exposure_prop_types(props['noises'])
        assert isinstance(props['path_score'], (float, int))
        assert isinstance(props['type'], str)
        assert props['type'] == 'quiet'
    return test_func


def test_path_set_1_shortest_path_prop_types(
    path_set_1, 
    test_line_geometry, 
    test_short_path_prop_types
):
    data = path_set_1
    path_fc = data['path_FC']
    s_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'short']
    assert len(s_paths) == 1
    s_path = s_paths[0]
    props = s_path['properties']
    test_line_geometry(s_path['geometry'])
    test_short_path_prop_types(props)


def test_path_set_1_quiet_path_prop_types(
    path_set_1, 
    test_line_geometry,
    test_quiet_path_prop_types
):
    data = path_set_1
    path_fc = data['path_FC']
    q_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'quiet']
    assert len(q_paths) == 3
    for qp in q_paths:
        test_line_geometry(qp['geometry'])
        test_quiet_path_prop_types(qp['properties'])


def test_path_set_1_shortest_path_geom(path_set_1):
    data = path_set_1
    path_fc = data['path_FC']
    s_path = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'short'][0]
    geom = s_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1340.0


def test_path_set_1_shortest_path_props(path_set_1):
    data = path_set_1
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
    assert props['missing_aqi'] == False
    assert props['missing_noises'] == False
    assert props['missing_gvi'] == False
    assert props['nei'] == 1955.2
    assert props['nei_diff'] == None
    assert props['nei_diff_rat'] == None # used in UI
    assert props['nei_norm'] == 0.62 # used in UI
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"55": 0.672, "60": 11.977, "65": 4.5, "70": 82.851}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"55": 9.008, "60": 160.5, "65": 60.298, "70": 1110.231}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"55": 9.008, "60": 160.5, "65": 60.298, "70": 342.653, "75": 767.578}'
    assert props['path_score'] is None
    assert props['type'] == 'short'


path_id_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.QUIET]
path_id = path_id_prefix + '1.3'


def test_path_set_1_quiet_path_geom(path_set_1):
    data = path_set_1
    path_fc = data['path_FC']
    q_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == path_id][0]
    geom = q_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1475.14


def test_path_set_1_quiet_path_props(path_set_1):
    data = path_set_1
    path_fc = data['path_FC']
    q_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == path_id][0]
    props = q_path['properties']
    assert props['cost_coeff'] == 1.3
    assert props['id'] == path_id
    assert props['len_diff'] == 135.1
    assert props['len_diff_rat'] == 10.1
    assert props['length'] == 1475.16
    assert props['length_b'] == 1954.72
    assert props['mdB'] == 55.1
    assert props['mdB_diff'] == -18.7
    assert props['missing_aqi'] == False
    assert props['missing_noises'] == False
    assert props['missing_gvi'] == False
    assert props['nei'] == 603.4
    assert props['nei_diff'] == -1351.8
    assert props['nei_diff_rat'] == -69.1
    assert props['nei_norm'] == 0.17
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"40": 29.049, "50": 16.106, "55": 26.281, "60": 28.359, "65": 0.204}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"40": 428.525, "50": 237.586, "55": 387.688, "60": 418.346, "65": 3.011}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"40": 33.96, "45": 394.565, "50": 237.586, "55": 387.688, "60": 418.346, "65": 3.011}'
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


def test_path_set_1_edge_fc(
    path_set_1, 
    test_line_geometry, 
    test_edge_props
):
    data = path_set_1
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
    path_set_1,
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
    # geom length
    coords = path_fc['features'][0]['geometry']['coordinates']
    line = LineString(coords)
    line_proj = project_geom(line)
    assert round(line_proj.length, 2) == 82.73
