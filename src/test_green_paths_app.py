import unittest
import pytest
import time
import pandas as pd
from datetime import datetime
import utils.files as file_utils
import utils.noise_exposures as noise_exps
import utils.utils as utils
import utils.tests as tests
import utils.graphs as graph_utils
from utils.graph_handler import GraphHandler
from utils.graph_aqi_updater import GraphAqiUpdater
import utils.aq_exposures as aq_exps
from utils.logger import Logger
from utils.path_aqi_attrs import PathAqiAttrs

# initialize graph
logger = Logger(b_printing=True, log_file='test_green_paths_app.log')
G = GraphHandler(logger, subset=True, set_noise_costs=True)

def get_quiet_path_stats(G, od_dict, logging=False):
    FC = tests.get_short_quiet_paths(logger, G, od_dict['orig_latLon'], od_dict['dest_latLon'], logging=logging)
    path_props = [feat['properties'] for feat in FC]
    paths_df = pd.DataFrame(path_props)
    sp = paths_df[paths_df['type'] == 'short']
    qp = paths_df[paths_df['type'] == 'quiet']
    sp_count = len(sp)
    qp_count = len(qp)
    sp_len = round(sp['length'].sum(), 1)
    qp_len_sum = round(qp['length'].sum(), 1)
    all_noises = noise_exps.aggregate_exposures(list(paths_df['noises']))
    noise_total_len = round(noise_exps.get_total_noises_len(all_noises), 1)
    set_stats = { 'sp_count': sp_count, 'qp_count': qp_count, 'sp_len': sp_len, 'qp_len_sum': qp_len_sum, 'noise_total_len': noise_total_len }
    qp_stats = tests.get_qp_feat_props_from_FC(FC)
    return { 'set_stats': set_stats, 'qp_stats': qp_stats }

# read OD pairs for routing tests
od_dict = tests.get_test_ODs()

class TestGraphAqiUpdater(unittest.TestCase):

    def test_aqi_updater(self):
        aqi_updater = GraphAqiUpdater(logger, G, aqi_dir='data/tests/aqi_cache/', start=False)
        expected_aqi_csv = aqi_updater.get_expected_aqi_data_name()
        # test expected aqi data file name
        self.assertEqual(len(expected_aqi_csv), 21)

    def test_graph_aqi_update(self):
        aqi_updater = GraphAqiUpdater(logger, G, aqi_dir='data/tests/aqi_cache/', start=False)
        aqi_edge_updates_csv = 'aqi_2019-11-08T14.csv'
        aqi_updater.read_update_aqi_to_graph(aqi_edge_updates_csv)
        edge_dicts = graph_utils.get_all_edge_dicts(G.graph)
        logger.debug('edge_dicts count: '+ str(len(edge_dicts)))
        # test that all edges got aqi attr
        all_edges_have_aqi = True
        for edge in edge_dicts:
            if ('aqi_exp' not in edge):
                all_edges_have_aqi = False
        self.assertEqual(all_edges_have_aqi, True, msg='One or more edges did not get aqi_exp')
        # test that all edges got aqi cost attrs
        all_edges_have_aqi_cost = True
        for edge in edge_dicts:
            if ('aqc_1' not in edge):
                all_edges_have_aqi_cost = False
        self.assertEqual(all_edges_have_aqi_cost, True, msg='One or more edges did not get aqi costs')
        eg_edge = edge_dicts[0]
        eg_aqi = eg_edge['aqi_exp'][0]
        self.assertAlmostEqual(eg_aqi, 1.87, places=2)
        self.assertAlmostEqual(eg_edge['aqc_3'], 209.95, places=2, msg='Expected aqc_3 cost was not set')

class TestGreenPaths(unittest.TestCase):
    
    def test_quiet_path_1(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 813.0, 'qp_len_sum': 843.3, 'noise_total_len': 402.5 }
        test_stats = get_quiet_path_stats(G, od_dict[1])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_5(self):
        set_stats = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 1648.8, 'qp_len_sum': 7540.9, 'noise_total_len': 6159.0 }
        qp_stats = {
            'id': 'q_0.5',
            'length': 1671.45,
            'len_diff': 22.7,
            'len_diff_rat': 1.4,
            'cost_coeff': 0.5,
            'mdB': 53.6,
            'nei': 370.4,
            'nei_norm': 0.22,
            'mdB_diff': -3.5,
            'nei_diff': -106.2,
            'nei_diff_rat': -22.3,
            'path_score': 4.7,
            'noise_diff_sum': -219.06,
            'noise_pcts_sum': 100.0,
            'geom_length': 1671.5
            }
        test_stats = get_quiet_path_stats(G, od_dict[5])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)

    def test_quiet_path_6(self):
        set_stats = { 'sp_count': 1, 'qp_count': 3, 'sp_len': 1024.9, 'qp_len_sum': 3699.8, 'noise_total_len': 4395.5 }
        qp_stats = {
            'id': 'q_1',
            'length': 1081.78,
            'len_diff': 56.9,
            'len_diff_rat': 5.6,
            'cost_coeff': 1,
            'mdB': 60.2,
            'nei': 377.7,
            'nei_norm': 0.35,
            'mdB_diff': -4.6,
            'nei_diff': -86.6,
            'nei_diff_rat': -18.7,
            'path_score': 1.5,
            'noise_pcts_sum': 100.1,
            'noise_diff_sum': 56.92,
            'geom_length': 1081.8
            }
        test_stats = get_quiet_path_stats(G, od_dict[6])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)

    def test_quiet_path_7(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 1054.2, 'qp_len_sum': 1338.5, 'noise_total_len': 2179.1 }
        test_stats = get_quiet_path_stats(G, od_dict[7])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_8(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 812.8, 'qp_len_sum': 2100.8, 'noise_total_len': 1505.8 }
        test_stats = get_quiet_path_stats(G, od_dict[8])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_9(self):
        set_stats = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 670.6, 'qp_len_sum': 3009.4, 'noise_total_len': 1776.9 }
        test_stats = get_quiet_path_stats(G, od_dict[9])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

if __name__ == '__main__':
    unittest.main()
