
import os
import json
import pytest


@pytest.fixture
def set_test_env(monkeypatch):
    monkeypatch.setenv('GRAPH_SUBSET', 'True')


@pytest.fixture
def client(set_test_env):
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
