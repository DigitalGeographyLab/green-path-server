#%%
import unittest
import pytest
import json
import time
import geopandas as gpd
from fiona.crs import from_epsg
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
import utils.quiet_paths as qp
import utils.utils as utils
import utils.tests as tests

#%% 
def get_short_quiet_paths(graph, from_latLon, to_latLon, logging=False):
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    # find origin and destination nodes from closest edges
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, nts=nts, db_costs=db_costs, logging=logging)
    dest_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, nts=nts, db_costs=db_costs, logging=logging, orig_node=orig_node)
    # utils.print_duration(start_time, 'Origin & destination nodes set.')
    # start_time = time.time()
    # get shortest path
    path_list = []
    shortest_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight='length')
    path_geom_noises = nw.aggregate_path_geoms_attrs(graph, shortest_path, weight='length', noises=True)
    path_list.append({**path_geom_noises, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        noise_cost_attr = 'nc_'+str(nt)
        shortest_path = rt.get_shortest_path(graph, orig_node['node'], dest_node['node'], weight=noise_cost_attr)
        path_geom_noises = nw.aggregate_path_geoms_attrs(graph, shortest_path, weight=noise_cost_attr, noises=True)
        path_list.append({**path_geom_noises, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    # remove linking edges of the origin / destination nodes
    nw.remove_new_node_and_link_edges(graph, orig_node)
    nw.remove_new_node_and_link_edges(graph, dest_node)
    # collect quiet paths to gdf
    paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = paths_gdf.drop_duplicates(subset=['type', 'total_length']).sort_values(by=['type', 'total_length'], ascending=[False, True])
    # add exposures to noise levels higher than specified threshods (dBs)
    paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add percentages of cumulative distances of different noise levels
    paths_gdf['noise_pcts'] = paths_gdf.apply(lambda row: exps.get_noise_pcts(row['noises'], row['total_length']), axis=1)
    # add noise exposure index (same as noise cost with noise tolerance: 1)
    paths_gdf['nei'] = [round(exps.get_noise_cost(noises=noises, db_costs=db_costs), 1) for noises in paths_gdf['noises']]
    paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 4), axis=1)
    return paths_gdf

#%% initialize graph
start_time = time.time()
nts = qp.get_noise_tolerances()
db_costs = qp.get_db_costs()
# graph = files.get_network_full_noise()
graph = files.get_network_kumpula_noise()
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
nw.set_graph_noise_costs(graph, edge_gdf, db_costs=db_costs, nts=nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

def get_od_path_stats(graph, od_dict, logging=False):
    paths = get_short_quiet_paths(graph, od_dict['orig_latLon'], od_dict['dest_latLon'], logging=logging)
    sp = paths[paths['type'] == 'short']
    qp = paths[paths['type'] == 'quiet']
    sp_count = len(sp)
    qp_count = len(qp)
    sp_len = round(sp['total_length'].sum(), 1)
    qp_len_sum = round(qp['total_length'].sum(), 1)
    all_noises = exps.aggregate_exposures(list(paths['noises']))
    noise_total_len = round(exps.get_total_noises_len(all_noises), 1)
    stats = { 'sp_count': sp_count, 'qp_count': qp_count, 'sp_len': sp_len, 'qp_len_sum': qp_len_sum, 'noise_total_len': noise_total_len }
    return stats

#%% read test OD pairs
od_dict = tests.get_test_ODs()

class TestQuietPaths(unittest.TestCase):

    def test_quiet_path_1(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 813.0, 'qp_len_sum': 813.0, 'noise_total_len': 618.5 }
        stats = get_od_path_stats(graph, od_dict[1])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_2(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 138.0, 'qp_len_sum': 138.0, 'noise_total_len': 276.0 }
        stats = get_od_path_stats(graph, od_dict[2])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_3(self):
        compare_d = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 936.5, 'qp_len_sum': 4688.3, 'noise_total_len': 4303.4 }
        stats = get_od_path_stats(graph, od_dict[3])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_4(self):
        compare_d = { 'sp_count': 1, 'qp_count': 5, 'sp_len': 1136.5, 'qp_len_sum': 6562.6, 'noise_total_len': 7263.1 }
        stats = get_od_path_stats(graph, od_dict[4])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_5(self):
        compare_d = { 'sp_count': 1, 'qp_count': 8, 'sp_len': 1648.8, 'qp_len_sum': 14334.3, 'noise_total_len': 11922.9 }
        stats = get_od_path_stats(graph, od_dict[5])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_6(self):
        compare_d = { 'sp_count': 1, 'qp_count': 5, 'sp_len': 1024.9, 'qp_len_sum': 6410.0, 'noise_total_len': 6782.7 }
        stats = get_od_path_stats(graph, od_dict[6])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_7(self):
        compare_d = { 'sp_count': 1, 'qp_count': 4, 'sp_len': 1053.4, 'qp_len_sum': 5120.3, 'noise_total_len': 5523.1 }
        stats = get_od_path_stats(graph, od_dict[7])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_8(self):
        compare_d = { 'sp_count': 1, 'qp_count': 6, 'sp_len': 795.9, 'qp_len_sum': 6318.3, 'noise_total_len': 5385.9 }
        stats = get_od_path_stats(graph, od_dict[8])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_9(self):
        compare_d = { 'sp_count': 1, 'qp_count': 2, 'sp_len': 670.6, 'qp_len_sum': 1364.7, 'noise_total_len': 1218.2 }
        stats = get_od_path_stats(graph, od_dict[9])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_10(self):
        compare_d = { 'sp_count': 1, 'qp_count': 5, 'sp_len': 1140.8, 'qp_len_sum': 6139.4, 'noise_total_len': 5969.7 }
        stats = get_od_path_stats(graph, od_dict[10])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_11(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 47.3, 'qp_len_sum': 47.3, 'noise_total_len': 94.6 }
        stats = get_od_path_stats(graph, od_dict[11])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_12(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 37.4, 'qp_len_sum': 37.4, 'noise_total_len': 74.8 }
        stats = get_od_path_stats(graph, od_dict[12])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_13(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 112.4, 'qp_len_sum': 112.4, 'noise_total_len': 224.8 }
        stats = get_od_path_stats(graph, od_dict[13])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_14(self):
        compare_d = { 'sp_count': 1, 'qp_count': 1, 'sp_len': 108.1, 'qp_len_sum': 108.1, 'noise_total_len': 216.3 }
        stats = get_od_path_stats(graph, od_dict[14])
        self.assertDictEqual(stats, compare_d)

    def test_quiet_path_15(self):
        compare_d = { 'sp_count': 1, 'qp_count': 2, 'sp_len': 513.7, 'qp_len_sum': 1133.4, 'noise_total_len': 1647.1 }
        stats = get_od_path_stats(graph, od_dict[15])
        self.assertDictEqual(stats, compare_d)

if __name__ == '__main__':
    unittest.main()
