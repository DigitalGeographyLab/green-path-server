from unittest.mock import patch
import pytest


__noise_sensitivities = [ 0.1, 0.4, 1.3, 3.5, 6 ]
__aq_sensitivities = [ 5, 15, 30 ]
__gvi_sensitivities = [ 2, 4, 8 ]


@pytest.fixture(scope='module')
def client():
    patch_env_research_mode = patch('gp_server.conf.research_mode', True)
    patch_env_edge_data = patch('gp_server.conf.edge_data', True)
    patch_env_graph_file = patch('gp_server.conf.graph_file', r'graphs/kumpula.graphml')
    
    patch_noise_sens = patch('gp_server.app.noise_exposures.get_noise_sensitivities', return_value=__noise_sensitivities)
    patch_aq_sens = patch('gp_server.app.aq_exposures.get_aq_sensitivities', return_value=__aq_sensitivities)
    patch_gvi_sens = patch('gp_server.app.greenery_exposures.get_gvi_sensitivities', return_value=__gvi_sensitivities)
    
    with patch_env_research_mode, patch_env_graph_file, patch_env_edge_data, patch_noise_sens, patch_aq_sens, patch_gvi_sens:
        from gp_server_main import app
        with app.test_client() as gp_client:
            yield gp_client
