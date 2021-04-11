import pytest
import json
from gp_server.app.constants import PathType


@pytest.fixture
def path_set_1(client) -> dict:
    response = client.get('/paths/bike/quiet/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 2
    yield data


def test_response_does_not_include_edge_fc(path_set_1):
    assert not path_set_1['edge_FC']


def test_no_safest_path_present_in_paths(path_set_1):
    feats = path_set_1['path_FC']['features']
    types = [feat['properties']['type'] for feat in feats]
    assert PathType.SAFEST.value not in types 


def test_fastest_path_not_present_in_paths(path_set_1):
    feats = path_set_1['path_FC']['features']
    types = [feat['properties']['type'] for feat in feats]
    assert PathType.FASTEST.value not in types 


def test_shortest_path_is_present_in_paths(path_set_1):
    feats = path_set_1['path_FC']['features']
    types = [feat['properties']['type'] for feat in feats]
    assert 'short' in types 
    assert feats[0]['properties']['type'] == 'short'


def test_quiet_paths_present_in_paths(path_set_1):
    feats = path_set_1['path_FC']['features']
    types = [feat['properties']['type'] for feat in feats]
    assert PathType.QUIET.value in types 


def test_paths_are_sorted_by_length(path_set_1):
    feats = path_set_1['path_FC']['features']
    lengths = [feat['properties']['length'] for feat in feats]
    prev_len = lengths[0]
    for len in lengths:
        assert len >= prev_len
        prev_len = len
