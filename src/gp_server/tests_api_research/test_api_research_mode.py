from typing import List
import pytest
import json
from gp_server.app.constants import PathType


@pytest.fixture
def green_bike_path_data(client) -> dict:
    response = client.get('/paths/bike/green/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 3
    yield data


@pytest.fixture
def quiet_walk_path_data(client) -> dict:
    response = client.get('/paths/walk/quiet/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 5
    yield data


@pytest.fixture
def feats_1(green_bike_path_data) -> List[dict]:
    return green_bike_path_data['path_FC']['features']


@pytest.fixture
def feats_2(quiet_walk_path_data) -> List[dict]:
    return quiet_walk_path_data['path_FC']['features']


def test_response_does_not_include_edge_fc(green_bike_path_data, quiet_walk_path_data):
    assert not green_bike_path_data['edge_FC']
    assert not quiet_walk_path_data['edge_FC']


def test_no_safest_path_present_in_paths(feats_1, feats_2):
    types = [feat['properties']['type'] for feat in feats_1]
    assert PathType.SAFEST.value not in types

    types = [feat['properties']['type'] for feat in feats_2]
    assert PathType.SAFEST.value not in types


def test_fastest_path_not_present_in_paths(feats_1, feats_2):
    types = [feat['properties']['type'] for feat in feats_1]
    assert PathType.FASTEST.value not in types 

    types = [feat['properties']['type'] for feat in feats_2]
    assert PathType.FASTEST.value not in types 


def test_one_shortest_path_is_present_in_paths(feats_1, feats_2):
    types = [feat['properties']['type'] for feat in feats_1]
    assert types.count('short') == 1
    assert feats_1[0]['properties']['type'] == 'short'
    assert feats_1[0]['properties']['id'] == 'short'

    types = [feat['properties']['type'] for feat in feats_2]
    assert types.count('short') == 1
    assert feats_2[0]['properties']['type'] == 'short'
    assert feats_2[0]['properties']['id'] == 'short'


def test_green_paths_are_included_in_paths(feats_1):
    types = [feat['properties']['type'] for feat in feats_1]
    assert types.count('green') == 2


def test_quiet_paths_are_included_in_paths(feats_2):
    types = [feat['properties']['type'] for feat in feats_2]
    assert types.count('quiet') == 4


def test_paths_are_sorted_by_length(feats_1, feats_2):
    lengths = [feat['properties']['length'] for feat in feats_1]
    prev_len = lengths[0]
    for len in lengths:
        assert len >= prev_len
        prev_len = len

    lengths = [feat['properties']['length'] for feat in feats_2]
    prev_len = lengths[0]
    for len in lengths:
        assert len >= prev_len
        prev_len = len


def test_edge_data_is_included_as_path_property(feats_1, feats_2):
    for feat in feats_1 + feats_2:
        assert 'edge_data' in feat['properties']


def test_edge_data_has_correct_properties(feats_1):
    edge_datas = [feat['properties']['edge_data'] for feat in feats_1]
    for edge_data in edge_datas:
        for ed in edge_data:
            assert isinstance(ed['length'], float)
            assert 'aqi' in ed
            assert isinstance(ed['gvi'], float)
            assert isinstance(ed['mdB'], float)
            assert isinstance(ed['coords_wgs'], list)
            assert isinstance(ed['coords_wgs'][0], list)


@pytest.fixture
def fastest_walk_path_features(client) -> dict:
    response = client.get('/paths/walk/fast/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    yield data['path_FC']['features']


def test_walk_routing_mode_fast_returns_only_one_path(fastest_walk_path_features):
    assert len(fastest_walk_path_features) == 1


def test_walk_routing_mode_fast_returns_path_with_type_short(fastest_walk_path_features):
    assert fastest_walk_path_features[0]['properties']['type'] == 'short'
    assert fastest_walk_path_features[0]['properties']['id'] == 'short'


@pytest.fixture
def fastest_bike_path_features(client) -> dict:
    response = client.get('/paths/bike/fast/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    yield data['path_FC']['features']


def test_bike_routing_mode_fast_returns_only_one_path(fastest_bike_path_features):
    assert len(fastest_bike_path_features) == 1


def test_bike_routing_mode_fast_returns_path_with_type_short(fastest_bike_path_features):
    assert fastest_bike_path_features[0]['properties']['type'] == 'short'
    assert fastest_bike_path_features[0]['properties']['id'] == 'short'


@pytest.fixture
def short_bike_path_features(client) -> dict:
    response = client.get('/paths/bike/short/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    yield data['path_FC']['features']


@pytest.fixture
def short_walk_path_features(client) -> dict:
    response = client.get('/paths/walk/short/60.21611655,24.978502127/60.20063978,24.964127292')
    data = json.loads(response.data)
    assert data['path_FC']['type'] == 'FeatureCollection'
    yield data['path_FC']['features']


def test_legacy_routing_mode_short_returns_path_with_type_short(short_bike_path_features, short_walk_path_features):
    assert len(short_bike_path_features) == 1
    assert len(short_walk_path_features) == 1
    assert short_bike_path_features[0]['properties']['type'] == 'short'
    assert short_bike_path_features[0]['properties']['id'] == 'short'
    assert short_walk_path_features[0]['properties']['type'] == 'short'
    assert short_walk_path_features[0]['properties']['id'] == 'short'
