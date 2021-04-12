from typing import List
import pytest
import json
from gp_server.app.constants import PathType


@pytest.fixture
def path_set_1(client) -> dict:
    response = client.get('/paths/bike/green/60.21611655,24.978502127/60.20063978,24.964127292')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 3
    yield data


@pytest.fixture
def path_set_2(client) -> dict:
    response = client.get('/paths/walk/quiet/60.21611655,24.978502127/60.20063978,24.964127292')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 5
    yield data


@pytest.fixture
def feats_1(path_set_1) -> List[dict]:
    return path_set_1['path_FC']['features']


@pytest.fixture
def feats_2(path_set_2) -> List[dict]:
    return path_set_2['path_FC']['features']


def test_response_does_not_include_edge_fc(path_set_1, path_set_2):
    assert not path_set_1['edge_FC']
    assert not path_set_2['edge_FC']


def test_no_safest_path_present_in_paths(feats_1, feats_2):
    types = tuple(feat['properties']['type'] for feat in feats_1)
    assert PathType.SAFEST.value not in types

    types = tuple(feat['properties']['type'] for feat in feats_2)
    assert PathType.SAFEST.value not in types


def test_fastest_path_not_present_in_paths(feats_1, feats_2):
    types = tuple(feat['properties']['type'] for feat in feats_1)
    assert PathType.FASTEST.value not in types 

    types = tuple(feat['properties']['type'] for feat in feats_2)
    assert PathType.FASTEST.value not in types 


def test_one_shortest_path_is_present_in_paths(feats_1, feats_2):
    types = tuple(feat['properties']['type'] for feat in feats_1)
    assert types.count('short') == 1
    assert feats_1[0]['properties']['type'] == 'short'

    types = tuple(feat['properties']['type'] for feat in feats_2)
    assert types.count('short') == 1
    assert feats_2[0]['properties']['type'] == 'short'


def test_green_paths_present_in_paths(feats_1, feats_2):
    types = tuple(feat['properties']['type'] for feat in feats_1)
    assert types.count('green') == 2


def test_quiet_paths_present_in_paths(feats_1, feats_2):
    types = tuple(feat['properties']['type'] for feat in feats_2)
    assert types.count('quiet') == 4


def test_paths_are_sorted_by_length(feats_1, feats_2):
    lengths = tuple(feat['properties']['length'] for feat in feats_1)
    prev_len = lengths[0]
    for len in lengths:
        assert len >= prev_len
        prev_len = len

    lengths = tuple(feat['properties']['length'] for feat in feats_2)
    prev_len = lengths[0]
    for len in lengths:
        assert len >= prev_len
        prev_len = len
