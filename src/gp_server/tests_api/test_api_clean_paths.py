from typing import Callable, Tuple
import json
import pytest
from shapely.geometry import LineString
from common.geometry import project_geom
from gp_server.app.constants import cost_prefix_dict, TravelMode, RoutingMode


@pytest.fixture
def path_set_1(client) -> dict:
    response = client.get('/paths/walk/clean/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) > 1
    assert len(data['edge_FC']['features']) > 1
    yield (data['edge_FC'], data['path_FC'])


@pytest.fixture
def test_fast_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['aqc'], (float, int))
        assert props['aqc_diff'] is None
        assert props['aqc_diff_rat'] is None
        assert props['aqc_diff_score'] is None
        assert isinstance(props['aqc_norm'], (float, int))
        test_exposure_prop_types(props['aqi_cl_exps'])
        assert isinstance(props['aqi_m'], (float, int))
        assert props['aqi_m_diff'] is None
        test_exposure_prop_types(props['aqi_cl_pcts'], 100.0)
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        assert props['id'] == 'fast'
        assert isinstance(props['len_diff'], (float, int))
        assert props['len_diff_rat'] is None
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['bike_time_cost'], (float, int))
        assert isinstance(props['bike_safety_cost'], (float, int))
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
        assert isinstance(props['type'], str)
        assert props['type'] == 'fast'
    return test_func


@pytest.fixture
def test_clean_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['aqc'], (float, int))
        assert isinstance(props['aqc_diff'], (float, int))
        assert isinstance(props['aqc_diff_rat'], (float, int))
        assert isinstance(props['aqc_diff_score'], (float, int))
        assert isinstance(props['aqc_norm'], (float, int))
        test_exposure_prop_types(props['aqi_cl_exps'])
        assert isinstance(props['aqi_m'], (float, int))
        assert isinstance(props['aqi_m_diff'], (float, int))
        test_exposure_prop_types(props['aqi_cl_pcts'], 100.0)
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        assert isinstance(props['len_diff'], (float, int))
        assert isinstance(props['len_diff_rat'], (float, int))
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['bike_time_cost'], (float, int))
        assert isinstance(props['bike_safety_cost'], (float, int))
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
        assert isinstance(props['type'], str)
        assert props['type'] == 'clean'
    return test_func


def test_path_set_1_fastest_path_prop_types(
    path_set_1, 
    test_line_geometry, 
    test_fast_path_prop_types
):
    _, path_fc = path_set_1
    s_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'fast']
    assert len(s_paths) == 1
    s_path = s_paths[0]
    props = s_path['properties']
    test_line_geometry(s_path['geometry'])
    test_fast_path_prop_types(props)


def test_path_set_1_clean_path_prop_types(
    path_set_1, 
    test_line_geometry,
    test_clean_path_prop_types
):
    _, path_fc = path_set_1
    c_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'clean']
    assert len(c_paths) == 1
    for qp in c_paths:
        test_line_geometry(qp['geometry'])
        test_clean_path_prop_types(qp['properties'])


def test_path_set_1_fastest_path_geom(path_set_1):
    _, path_fc = path_set_1
    s_path = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'fast'][0]
    geom = s_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1340.0


def test_path_set_1_fastest_path_props(path_set_1):
    _, path_fc = path_set_1
    s_path = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'fast'][0]
    props = s_path['properties']
    assert props['aqc'] == 177.86
    assert props['aqc_norm'] == 0.133
    assert json.dumps(props['aqi_cl_exps'], sort_keys=True) == '{"1": 81.004, "2": 1259.033}'
    assert props['aqi_m'] == 1.53
    assert json.dumps(props['aqi_cl_pcts'], sort_keys=True) == '{"1": 6.045, "2": 93.955}'
    assert props['cost_coeff'] == 0
    assert props['id'] == 'fast'
    assert props['len_diff'] == 0
    assert props['length'] == 1340.04
    assert props['bike_time_cost'] == 1340.2
    assert props['mdB'] == 73.8
    assert not props['missing_aqi']
    assert not props['missing_noises']
    assert not props['missing_gvi']
    assert props['nei'] == 1955.2
    assert props['nei_norm'] == 0.62
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"55": 0.672, "60": 11.977, "65": 4.5, "70": 82.851}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"55": 9.008, "60": 160.5, "65": 60.298, "70": 1110.231}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"55": 9.008, "60": 160.5, "65": 60.298, "70": 342.653, "75": 767.578}'
    assert props['type'] == 'fast'


path_id_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.CLEAN]
path_id = path_id_prefix + '15'


def test_path_set_1_clean_path_geom(path_set_1):
    _, path_fc = path_set_1
    c_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == path_id][0]
    geom = c_path['geometry']
    line = LineString(geom['coordinates'])
    proj_line = project_geom(line)
    assert round(proj_line.length, 2) == 1372.8


def test_path_set_1_clean_path_props(path_set_1):
    _, path_fc = path_set_1
    c_path = [feat for feat in path_fc['features'] if feat['properties']['id'] == path_id][0]
    props = c_path['properties']
    assert props['aqc'] == 174.64
    assert props['aqc_diff'] == -3.22
    assert props['aqc_diff_rat'] == -1.8
    assert props['aqc_diff_score'] == 0.1
    assert props['aqc_norm'] == 0.127
    assert json.dumps(props['aqi_cl_exps'], sort_keys=True) == '{"1": 290.019, "2": 1082.854}'
    assert props['aqi_m'] == 1.51
    assert props['aqi_m_diff'] == -0.02
    assert json.dumps(props['aqi_cl_pcts'], sort_keys=True) == '{"1": 21.125, "2": 78.875}'
    assert props['cost_coeff'] == 15
    assert props['id'] == path_id
    assert props['len_diff'] == 32.8
    assert props['len_diff_rat'] == 2.4
    assert props['length'] == 1372.87
    assert props['bike_time_cost'] == 1581.6
    assert props['mdB'] == 69.2
    assert props['mdB_diff'] == -4.6
    assert not props['missing_aqi']
    assert not props['missing_noises']
    assert not props['missing_gvi']
    assert props['nei'] == 1540.3
    assert props['nei_diff'] == -414.9
    assert props['nei_diff_rat'] == -21.2
    assert props['nei_norm'] == 0.48
    assert json.dumps(props['noise_pcts'], sort_keys=True) == '{"55": 0.656, "60": 47.114, "65": 5.324, "70": 46.906}'
    assert json.dumps(props['noise_range_exps'], sort_keys=True) == '{"55": 9.008, "60": 646.815, "65": 73.09, "70": 643.961}'
    assert json.dumps(props['noises'], sort_keys=True) == '{"55": 9.008, "60": 646.815, "65": 73.09, "70": 157.939, "75": 486.022}'
    assert props['type'] == 'clean'


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
    edge_fc, path_fc = path_set_1
    assert edge_fc['type'] == 'FeatureCollection'
    assert isinstance(edge_fc['features'], list)
    assert len(edge_fc['features']) == 14
    for feat in edge_fc['features']:
        assert feat['type'] == 'Feature'
        test_line_geometry(feat['geometry'])
        test_edge_props(feat['properties'])
    
    # test that same paths (ids) are present in both edge_FC and path_FC
    path_ids_in_edges = set([feat['properties']['path'] for feat in edge_fc['features']])
    assert len(path_ids_in_edges) == len(path_fc['features'])
    assert path_ids_in_edges == set([path['properties']['id'] for path in path_fc['features']])


@pytest.fixture
def clean_paths_on_one_street(client) -> Tuple[dict]:
    """Returns paths with origin and destination on the same street."""
    response = client.get('/paths/walk/clean/60.214233,24.971411/60.213558,24.970785')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert data['edge_FC']['type'] == 'FeatureCollection'
    yield (data['edge_FC'], data['path_FC'])


def test_clean_paths_on_same_street(
    path_set_1,
    clean_paths_on_one_street,
    test_line_geometry, 
    test_fast_path_prop_types,
    test_edge_props
):
    """Tests that if origin and destination are on the same street, the resultsets are still as expected."""
    edge_fc, path_fc = clean_paths_on_one_street
    # edges
    assert len(edge_fc['features']) == 1
    test_line_geometry(edge_fc['features'][0]['geometry'])
    test_edge_props(edge_fc['features'][0]['properties'])
    # paths
    assert len(path_fc['features']) == 1
    test_line_geometry(path_fc['features'][0]['geometry'])
    test_fast_path_prop_types(path_fc['features'][0]['properties'])
    # geom length
    coords = path_fc['features'][0]['geometry']['coordinates']
    line = LineString(coords)
    line_proj = project_geom(line)
    assert round(line_proj.length, 2) == 82.73
