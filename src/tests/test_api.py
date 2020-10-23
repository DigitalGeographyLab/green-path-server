
import os
import json
from green_paths_app import app


os.environ['GRAPH_SUBSET'] = 'True'
client = app.test_client()


def test_endpoint():
    response = client.get('/')
    assert response.status_code == 200


def test_aqi_status_path():
    response = client.get('/aqistatus')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['aqi_data_updated'] == False
    assert data['aqi_data_utc_time_secs'] == None


def test_aqi_map_data_path():
    response = client.get('/aqi-map-data')
    assert response.status_code == 200
    assert response.get_data().decode('utf-8') == ''
