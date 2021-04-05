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


def test_invalid_request_path_error_response(client):
    response = client.get('/paths/walkASDF/quiet/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 400
    assert 'error_key' in json.loads(response.data)
    response = client.get('/paths/walk/quietASDF/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 400
    assert 'error_key' in json.loads(response.data)


def test_same_od_error_response(client):
    response = client.get('/paths/walk/quiet/60.212031,24.968584/60.212031,24.968584')
    assert response.status_code == 400
    assert 'error_key' in json.loads(response.data)


def test_od_not_found_error_response(client):
    response = client.get('/paths/walk/quiet/160.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 404
    assert 'error_key' in json.loads(response.data)
    response = client.get('/paths/walk/quiet/60.212031,24.968584/160.201520,24.961191')
    assert response.status_code == 404
    assert 'error_key' in json.loads(response.data)


def test_route_only_fastest_walk_path(client):
    response = client.get('/paths/walk/fast/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 1
    assert data['path_FC']['features'][0]['properties']['type'] == 'fast'
    assert data['path_FC']['features'][0]['properties']['id'] == 'fast'
    assert len(data['edge_FC']['features']) > 1


def test_route_only_fastest_bike_path(client):
    response = client.get('/paths/bike/fast/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 1
    assert data['path_FC']['features'][0]['properties']['type'] == 'fast'
    assert data['path_FC']['features'][0]['properties']['id'] == 'fast'
    assert len(data['edge_FC']['features']) > 1


def test_route_only_safest_bike_path(client):
    response = client.get('/paths/bike/safe/60.212031,24.968584/60.201520,24.961191')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert 'edge_FC' in data
    assert 'path_FC' in data
    assert data['path_FC']['type'] == 'FeatureCollection'
    assert len(data['path_FC']['features']) == 1
    assert data['path_FC']['features'][0]['properties']['type'] == 'safe'
    assert data['path_FC']['features'][0]['properties']['id'] == 'safe'
    assert len(data['edge_FC']['features']) > 1
