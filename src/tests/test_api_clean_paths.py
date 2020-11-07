import json


def test_aqi_status_path(client):
    response = client.get('/aqistatus')
    data = json.loads(response.data)
    assert data['aqi_data_updated']
    assert data['aqi_data_utc_time_secs'] == 1603634400
