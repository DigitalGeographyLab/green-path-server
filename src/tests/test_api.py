import json


def test_endpoint(client):
    response = client.get('/')
    response.get_data().decode('utf-8') == 'Keep calm and walk green paths.'
    assert response.status_code == 200


def test_aq_routing_status_path(client):
    response = client.get('/aqistatus')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert 'aqi_data_updated' in status
    assert 'aqi_data_utc_time_secs' in status


def test_aq_routing_available(client):
    response = client.get('/aqistatus')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert status['aqi_data_updated'] 
    assert status['aqi_data_utc_time_secs'] == 1603634400 


def test_aqi_map_data_status_path(client):
    response = client.get('/aqi-map-data-status')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert 'aqi_map_data_available' in status
    assert 'aqi_map_data_utc_time_secs' in status


def test_aqi_map_data_available(client):
    response = client.get('/aqi-map-data-status')
    assert response.status_code == 200
    status = json.loads(response.data)
    assert status['aqi_map_data_available']
    assert status['aqi_map_data_utc_time_secs'] == 1603634400


def test_aqi_map_data_path(client):
    response = client.get('/aqi-map-data')
    assert response.status_code == 200


def test_aqi_map_data_response(client):
    response = client.get('/aqi-map-data')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['data']) == 387411 
