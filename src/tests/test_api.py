import json


def test_endpoint(client):
    response = client.get('/')
    response.get_data().decode('utf-8') == 'Keep calm and walk green paths.'
    assert response.status_code == 200


def test_aqi_status_path(client):
    response = client.get('/aqistatus')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert 'aqi_data_updated' in status
    assert 'aqi_data_utc_time_secs' in status


def test_aqi_map_data_status_path(client):
    response = client.get('/aqi-map-data-status')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert 'aqi_map_data_available' in status
    assert 'aqi_map_data_utc_time_secs' in status


def test_aqi_map_data_path(client):
    response = client.get('/aqi-map-data')
    assert response.status_code == 200
