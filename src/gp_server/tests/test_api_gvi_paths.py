from typing import Callable
import json
import pytest


@pytest.fixture
def path_set_1(client) -> dict:
    response = client.get('/paths/bike/green/60.215175,24.980636/60.200423,24.961936')
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
def test_fast_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict):
        assert isinstance(props['cost_coeff'], (float, int))
        assert isinstance(props['id'], str)
        test_exposure_prop_types(props['gvi_cl_exps'])
        test_exposure_prop_types(props['gvi_cl_pcts'], expected_sum=100.0)
        assert isinstance(props['gvi_m'], (float, int))
        assert props['gvi_m_diff'] is None
        assert props['id'] == 'fast'
        assert isinstance(props['len_diff'], (float, int))
        assert props['len_diff_rat'] is None
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['bike_time_cost'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert props['mdB_diff'] is None
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['missing_gvi'], bool)
        assert isinstance(props['nei'], (float, int))
        assert props['nei_diff'] is None
        assert props['nei_diff_rat'] is None
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'])
        test_exposure_prop_types(props['noise_range_exps'])
        test_exposure_prop_types(props['noises'])
        assert props['path_score'] is None
        assert isinstance(props['type'], str)
        assert props['type'] == 'fast'
    return test_func


@pytest.fixture
def test_gvi_path_prop_types(test_exposure_prop_types) -> Callable[[dict], None]:
    def test_func(props: dict, expected_path_type='green'):
        assert isinstance(props['cost_coeff'], (float, int))
        test_exposure_prop_types(props['gvi_cl_exps'])
        test_exposure_prop_types(props['gvi_cl_pcts'], expected_sum=100.0)
        assert isinstance(props['gvi_m'], (float, int))
        assert isinstance(props['gvi_m_diff'], (float, int))
        assert isinstance(props['id'], str)
        assert isinstance(props['len_diff'], (float, int))
        assert isinstance(props['len_diff_rat'], (float, int))
        assert isinstance(props['length'], (float, int))
        assert isinstance(props['bike_time_cost'], (float, int))
        assert isinstance(props['mdB'], (float, int))
        assert isinstance(props['mdB_diff'], (float, int))
        assert isinstance(props['missing_aqi'], bool)
        assert isinstance(props['missing_noises'], bool)
        assert isinstance(props['missing_gvi'], bool)
        assert isinstance(props['nei'], (float, int))
        assert isinstance(props['nei_diff'], (float, int))
        assert isinstance(props['nei_diff_rat'], (float, int))
        assert isinstance(props['nei_norm'], (float, int))
        test_exposure_prop_types(props['noise_pcts'])
        test_exposure_prop_types(props['noise_range_exps'])
        test_exposure_prop_types(props['noises'])
        assert isinstance(props['path_score'], (float, int))
        assert isinstance(props['type'], str)
        assert props['type'] == expected_path_type
    return test_func


def test_path_set_1_bike_path_types(
    path_set_1, 
):
    data = path_set_1
    path_fc = data['path_FC']

    for idx, feat in enumerate(path_fc['features']):
        if idx == 0:
            assert feat['properties']['type'] == 'fast'
            assert feat['properties']['id'] == 'fast'
        if idx == 1:
            assert feat['properties']['type'] == 'safe'
            assert feat['properties']['id'] == 'safe'
        if idx > 1:
            assert feat['properties']['type'] == 'green'
            assert 'c_g' in feat['properties']['id'] 


def test_path_set_1_fastest_path_prop_types(
    path_set_1, 
    test_line_geometry, 
    test_fast_path_prop_types
):
    data = path_set_1
    path_fc = data['path_FC']
    s_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'fast']
    assert len(s_paths) == 1
    s_path = s_paths[0]
    props = s_path['properties']
    test_line_geometry(s_path['geometry'])
    test_fast_path_prop_types(props)


def test_path_set_1_gvi_path_prop_types(
    path_set_1, 
    test_line_geometry,
    test_gvi_path_prop_types
):
    data = path_set_1
    path_fc = data['path_FC']
    gvi_paths = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'green']
    assert len(gvi_paths) == 1
    for gp in gvi_paths:
        test_line_geometry(gp['geometry'])
        test_gvi_path_prop_types(gp['properties'])


def test_path_set_1_safest_path_prop_types(
    path_set_1,
    test_line_geometry,
    test_gvi_path_prop_types
):
    data = path_set_1
    path_fc = data['path_FC']
    safest_path = [feat for feat in path_fc['features'] if feat['properties']['type'] == 'safe']
    assert len(safest_path) == 1
    for gp in safest_path:
        test_line_geometry(gp['geometry'])
        test_gvi_path_prop_types(gp['properties'], 'safe')


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
    assert len(edge_fc['features']) > 10
    for feat in edge_fc['features']:
        assert feat['type'] == 'Feature'
        test_line_geometry(feat['geometry'])
        test_edge_props(feat['properties'])
    
    # test that same paths (ids) are present in both edge_FC and path_FC
    path_ids_in_edges = set([feat['properties']['path'] for feat in edge_fc['features']])
    assert len(path_ids_in_edges) == len(path_fc['features'])
    assert path_ids_in_edges == set([path['properties']['id'] for path in path_fc['features']])
