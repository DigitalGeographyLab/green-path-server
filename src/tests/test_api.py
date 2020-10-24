
import os
import json
from green_paths_app import app


os.environ['GRAPH_SUBSET'] = 'True'
client = app.test_client()


def test_endpoint():
    response = client.get('/')
    response.get_data().decode('utf-8') == 'Keep calm and walk green paths.'
    assert response.status_code == 200


def test_aqi_status_path():
    response = client.get('/aqistatus')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['aqi_data_updated'] == False
    assert data['aqi_data_utc_time_secs'] == None


def test_aqi_map_data_status_path():
    response = client.get('/aqi-map-data-status')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert status['aqi_map_data_available'] == False
    assert status['aqi_map_data_utc_time_secs'] == None


def test_aqi_map_data_path():
    response = client.get('/aqi-map-data')
    assert response.status_code == 200
    # before first AQI map data load it should return just empty string
    assert response.get_data().decode('utf-8') == ''
