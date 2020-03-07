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
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# initialize graph
logger = Logger(b_printing=True, log_file='test_green_paths_app.log')
G = GraphHandler(logger, subset=True, set_noise_costs=True)
expected_ecount = G.graph.ecount()
expected_vcount = G.graph.vcount()
aqi_updater = GraphAqiUpdater(logger, G, aqi_dir='data/tests/aqi_cache/', start=False)
aqi_edge_updates_csv = 'aqi_2019-11-08T14.csv'
aqi_updater.read_update_aqi_to_graph(aqi_edge_updates_csv)

def get_quiet_path_stats(G, od_dict, logging=False):
    FC = tests.get_short_green_paths(logger, 'quiet', G, od_dict['orig_latLon'], od_dict['dest_latLon'], logging=logging)
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

def get_clean_path_stats(G, od_dict, logging=False):
    FC = tests.get_short_green_paths(logger, 'clean', G, od_dict['orig_latLon'], od_dict['dest_latLon'], logging=logging)
    path_props = [feat['properties'] for feat in FC]
    paths_df = pd.DataFrame(path_props)
    sp = paths_df[paths_df['type'] == 'short']
    cp = paths_df[paths_df['type'] == 'clean']
    sp_count = len(sp)
    cp_count = len(cp)
    sp_len = round(sp['length'].sum(), 1)
    cp_len_sum = round(cp['length'].sum(), 1)
    set_stats = { 'sp_count': sp_count, 'cp_count': cp_count, 'sp_len': sp_len, 'cp_len_sum': cp_len_sum }
    cp_stats = tests.get_cp_feat_props_from_FC(FC)
    return { 'set_stats': set_stats, 'cp_stats': cp_stats }

# read OD pairs for routing tests
od_dict = tests.get_test_ODs()

class TestGraphAqiUpdater(unittest.TestCase):

    def test_aqi_updater(self):
        aqi_updater = GraphAqiUpdater(logger, G, aqi_dir='data/tests/aqi_cache/', start=False)
        expected_aqi_csv = aqi_updater.get_expected_aqi_data_name()
        # test expected aqi data file name
        self.assertEqual(len(expected_aqi_csv), 21)

    def test_graph_aqi_update(self):
        # test that all edges got aqi attr and costs
        for edge in G.graph.es:
            edge_attrs = edge.attributes()
            self.assertIn('aqi_exp', edge_attrs.keys())
            self.assertIn('aqc_1', edge_attrs.keys())
            self.assertIsInstance(edge_attrs['aqc_3'], float)
            self.assertEqual(edge_attrs['has_aqi'], True)
            # check that graph is valid
            self.assertEqual(edge.source, edge_attrs['uvkey'][0])
            self.assertEqual(edge.target, edge_attrs['uvkey'][1])
        eg_edge = G.get_edge_by_id(0)
        eg_aqi = eg_edge['aqi_exp'][0]
        self.assertAlmostEqual(eg_aqi, 1.87, places=2)
        self.assertAlmostEqual(eg_edge['aqc_3'], 209.95, places=2, msg='Expected aqc_3 cost was not set')

class TestGreenPaths(unittest.TestCase):

    def test_exposure_attributes(self):
        FC = tests.get_short_green_paths(logger, 'quiet', G, od_dict[5]['orig_latLon'], od_dict[5]['dest_latLon'])
        for feature in FC:
            if (feature['properties']['type'] == 'quiet'):
                qp_feat = feature
                break
        qp_props = qp_feat['properties']
        self.assertAlmostEqual(qp_props['length'], noise_exps.get_total_noises_len(qp_props['noises']), 1)

    def test_quiet_path_1(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 813.0, 'qp_len_sum': 843.3, 'noise_total_len': 1656.3 }
        test_stats = get_quiet_path_stats(G, od_dict[1])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_quiet_path_5(self):
        set_stats = { 'sp_count': 1, 'qp_count': 3, 'sp_len': 1648.8, 'qp_len_sum': 5365.8, 'noise_total_len': 7014.6 }
        qp_stats = {
            'id': 'q_0.2',
            'length': 1671.45,
            'len_diff': 22.7,
            'len_diff_rat': 1.4,
            'cost_coeff': 0.2,
            'mdB': 53.6,
            'nei': 660.7,
            'nei_norm': 0.22,
            'mdB_diff': -3.5,
            'nei_diff': -189.4,
            'nei_diff_rat': -22.3,
            'path_score': 8.3,
            'noise_diff_sum': 22.68,
            'noise_pcts_sum': 100.0,
            'geom_length': 1671.5
            }
        test_stats = get_quiet_path_stats(G, od_dict[5])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        print(test_stats['qp_stats'])
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_quiet_path_6(self):
        set_stats = { 'sp_count': 1, 'qp_count': 3, 'sp_len': 1024.9, 'qp_len_sum': 3697.6, 'noise_total_len': 4722.4 }
        qp_stats = {
            'id': 'q_0.5',
            'length': 1081.78,
            'len_diff': 56.9,
            'len_diff_rat': 5.6,
            'cost_coeff': 0.5,
            'mdB': 60.2,
            'nei': 673.6,
            'nei_norm': 0.35,
            'mdB_diff': -4.6,
            'nei_diff': -153.9,
            'nei_diff_rat': -18.6,
            'path_score': 2.7,
            'noise_pcts_sum': 100.1,
            'noise_diff_sum': 56.92,
            'geom_length': 1081.8
            }
        test_stats = get_quiet_path_stats(G, od_dict[6])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        print(test_stats['qp_stats'])
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_quiet_path_7(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 1054.2, 'qp_len_sum': 1338.5, 'noise_total_len': 2392.7 }
        test_stats = get_quiet_path_stats(G, od_dict[7])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_quiet_path_8(self):
        set_stats = { 'sp_count': 1, 'qp_count': 0, 'sp_len': 812.8, 'qp_len_sum': 0.0, 'noise_total_len': 812.8 }
        test_stats = get_quiet_path_stats(G, od_dict[8])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_quiet_path_9(self):
        set_stats = { 'sp_count': 1, 'qp_count': 3, 'sp_len': 670.6, 'qp_len_sum': 2325.7, 'noise_total_len': 2996.3 }
        test_stats = get_quiet_path_stats(G, od_dict[9])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertEqual(G.graph.ecount(), expected_ecount)
        self.assertEqual(G.graph.vcount(), expected_vcount)

    def test_clean_path_1(self):
        cp_stats = {
            'id': 'aq_20', 
            'length': 1677.75, 
            'len_diff': 29.0,
            'len_diff_rat': 1.8,
            'cost_coeff': 20,
            'aqi_m': 1.88,
            'aqc': 369.09,
            'aqc_norm': 0.22,
            'aqi_cl_exps': {1: 1570.13, 2: 107.63},
            'aqi_pcts': {1: 93.59, 2: 6.42},
            'aqi_m_diff': -0.02,
            'aqc_diff': -2.1,
            'aqc_diff_rat': -0.6,
            'geom_length': 1677.8,
            'aqc_diff_score': 0.1
        }
        set_stats = { 'sp_count': 1, 'cp_count': 1, 'sp_len': 1648.8, 'cp_len_sum': 1677.8 }
        test_stats = get_clean_path_stats(G, od_dict[5])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertDictEqual(test_stats['cp_stats'], cp_stats)

if __name__ == '__main__':
    unittest.main()
