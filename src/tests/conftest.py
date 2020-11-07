from unittest.mock import patch, MagicMock
import pytest
import json
import time


@pytest.fixture(scope='module')
def monkeymodule():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='module')
def clean_path_test_env(monkeymodule):
    monkeymodule.setenv('GRAPH_SUBSET', 'True')
    monkeymodule.setenv('TEST_MODE', 'True')


@pytest.fixture(scope='module')
def initial_client(clean_path_test_env):
    mock = MagicMock(return_value=[ 0.1, 0.4, 1.3, 3.5, 6 ])
    with patch('utils.noise_exposures.get_noise_sensitivities', mock):
        from green_paths_app import app
        with app.test_client() as gp_client:
            yield gp_client


@pytest.fixture(scope='module')
def client(initial_client):
    """Returns API client only when it has loaded AQI data to the routing graph."""
    for _ in range(25):
        response = initial_client.get('/aqistatus')
        assert response.status_code == 200
        data = json.loads(response.data)
        if not data['aqi_data_updated']:
            time.sleep(1)
            continue
        break
    yield initial_client
