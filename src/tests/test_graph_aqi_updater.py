import pytest
from utils.igraphs import Edge as E 
from app.logger import Logger
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater


# initialize graph & graph AQI updater
log = Logger(b_printing=False)
G = GraphHandler(log, subset=True)
expected_ecount = G.graph.ecount()
expected_vcount = G.graph.vcount()

aqi_updater = GraphAqiUpdater(log, G, aqi_dir='tests/aqi_cache/')


def test_initial_aqi_updater_status():
    aqi_status = aqi_updater.get_aqi_update_status_response()
    assert aqi_status['aqi_data_updated'] == False
    assert aqi_status['aqi_data_utc_time_secs'] == None


def test_aqi_graph_update():
    # do AQI -> graph update
    aqi_edge_updates_csv = 'aqi_2019-11-08T14.csv'
    aqi_updater._GraphAqiUpdater__read_update_aqi_to_graph(aqi_edge_updates_csv)
    # check the updated graph (edge attributes)
    aqi_updates = []
    for e in G.graph.es:
        aqi_updates.append(e.attributes()[E.aqi.value])
    assert len(aqi_updates) == 16643
    aqi_updates_ok = [aqi for aqi in aqi_updates if aqi]
    aqi_updates_none = [aqi for aqi in aqi_updates if not aqi]
    assert len(aqi_updates_ok) == 16469
    assert len(aqi_updates_none) == 174


def test_aqi_updater_status_response():
    aqi_status = aqi_updater.get_aqi_update_status_response()
    assert aqi_status['aqi_data_updated'] == True
    assert aqi_status['aqi_data_utc_time_secs'] ==  1573221600
