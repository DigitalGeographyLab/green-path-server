import unittest
import pytest
import time
import pandas as pd
from datetime import datetime
import utils.files as file_utils
import utils.noise_exposures as noise_exps
import utils.utils as utils
import utils.tests as tests
from utils.graph_handler import GraphHandler

# graph_aqi_update_interval_secs: int = 20
debug: bool = True

# load graph data
start_time = time.time()
G = GraphHandler(subset=True)
G.set_noise_costs_to_edges()

# setup scheduled graph updater
# def edge_attr_update():
#     # TODO load AQI layer, calculate & update AQI costs to graph
#     G.update_current_time_to_graph()

# graph_updater = BackgroundScheduler()
# graph_updater.add_job(edge_attr_update, 'interval', seconds=graph_aqi_update_interval_secs)
# graph_updater.start()

utils.print_duration(start_time, 'graph initialized')

def get_quiet_path_stats(G, od_dict, logging=False):
    FC = tests.get_short_quiet_paths(G, od_dict['orig_latLon'], od_dict['dest_latLon'], logging=logging)
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

#%% read test OD pairs
od_dict = tests.get_test_ODs()

class TestQuietPaths(unittest.TestCase):
    
    maxDiff = None

    def test_quiet_path_1(self):
        set_stats = { 'sp_count': 1, 'qp_count': 0, 'sp_len': 813.0, 'qp_len_sum': 0.0, 'noise_total_len': 309.3 }
        test_stats = get_quiet_path_stats(G, od_dict[1])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_5(self):
        set_stats = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 1648.8, 'qp_len_sum': 7437.2, 'noise_total_len': 6735.1 }
        qp_stats = {
            'id': 'q_1',
            'length': 1671.45,
            'len_diff': 22.7,
            'len_diff_rat': 1.4,
            'cost_coeff': 1,
            'mdB': 53.6,
            'nei': 247.4,
            'nei_norm': 0.25,
            'mdB_diff': -3.5,
            'nei_diff': -88.0,
            'nei_diff_rat': -26.2,
            'path_score': 3.9,
            'noise_diff_sum': -219.06,
            'noise_pcts_sum': 100.0
            }
        test_stats = get_quiet_path_stats(G, od_dict[5])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)

    def test_quiet_path_6(self):
        set_stats = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 1024.9, 'qp_len_sum': 5385.1, 'noise_total_len': 5759.3 }
        qp_stats = {
            'id': 'q_1',
            'length': 1081.79,
            'len_diff': 56.9,
            'len_diff_rat': 5.6,
            'cost_coeff': 1,
            'mdB': 60.2,
            'nei': 274.9,
            'nei_norm': 0.42,
            'mdB_diff': -4.6,
            'nei_diff': -79.8,
            'nei_diff_rat': -22.5,
            'path_score': 1.4,
            'noise_diff_sum': 56.92,
            'noise_pcts_sum': 100.1
            }
        test_stats = get_quiet_path_stats(G, od_dict[6])
        self.assertDictEqual(test_stats['set_stats'], set_stats)
        self.assertDictEqual(test_stats['qp_stats'], qp_stats)

    def test_quiet_path_7(self):
        set_stats = { 'sp_count': 1, 'qp_count': 2, 'sp_len': 1054.2, 'qp_len_sum': 2704.9, 'noise_total_len': 3322.0 }
        test_stats = get_quiet_path_stats(G, od_dict[7])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_8(self):
        set_stats = { 'sp_count': 1, 'qp_count': 3, 'sp_len': 799.6, 'qp_len_sum': 3925.4, 'noise_total_len': 3252.8 }
        test_stats = get_quiet_path_stats(G, od_dict[8])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

    def test_quiet_path_9(self):
        set_stats = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 670.6, 'qp_len_sum': 694.1, 'noise_total_len': 806.6 }
        test_stats = get_quiet_path_stats(G, od_dict[9])
        self.assertDictEqual(test_stats['set_stats'], set_stats)

if __name__ == '__main__':
    unittest.main()
