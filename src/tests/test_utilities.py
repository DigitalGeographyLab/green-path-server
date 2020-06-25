import unittest
import pytest
import geopandas as gpd
import time
from shapely.geometry import Point, LineString
import utils.igraphs as ig_utils
import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps
import app.files as file_utils
import utils.routing as rt
import utils.aq_exposures as aq_exps
import app.tests as tests
from app.path_aqi_attrs import PathAqiAttrs
from app.graph_handler import GraphHandler
from app.graph_aqi_updater import GraphAqiUpdater
from app.logger import Logger

# read data
walk = tests.get_update_test_walk_line()
walk_geom = walk.loc[0, 'geometry']
# noise_polys = file_utils.get_noise_polygons()

# initialize graph
logger = Logger(b_printing=True, log_file='test_utilities.log')
G = GraphHandler(logger, subset=True)

def find_edges_between_node_pair(self, graph, source: int, target: int, directed: bool = False) -> List[dict]:
    try:
        if (directed == True):
            return [e.attributes() for e in self.graph.es.select(_source=source, _target=target)]
        else:
            return [e.attributes() for e in self.graph.es.select(_within=[source, target])]
    except Exception:
        self.log.warning('tried to find edges from/to invalid vertex id: '+ str(source) +' or: '+ str(target))
        return []

# @unittest.SkipTest
class TestIgraphUtils(unittest.TestCase):

    def test_convert_nx_graph_to_igraph(self):
        nx_graph = file_utils.load_graph_kumpula_noise()
        G = ig_utils.convert_nx_2_igraph(nx_graph)
        self.assertEqual(G.ecount(), 11931)
        for edge in G.es:
            self.assertEqual(len(edge.attributes().keys()), 5)
            self.assertIsInstance(edge['name'], int)
            self.assertIsInstance(edge['uvkey'], tuple)
            self.assertIsInstance(edge['length'], float)
            self.assertIsInstance(edge['noises'], dict)
            self.assertIsInstance(edge['geometry'], LineString)
            self.assertEqual(edge['uvkey'][0], edge.source)
            self.assertEqual(edge['uvkey'][1], edge.target)
        for vertex in G.vs:
            self.assertEqual(len(vertex.attributes().keys()), 2)
            self.assertIsInstance(vertex['name'], int)
            self.assertIsInstance(vertex['point'], Point)

    @unittest.skip('too slow')
    def test_convert_full_nx_graph_to_igraph(self):
        nx_graph = file_utils.load_graph_full_noise()
        G = ig_utils.convert_nx_2_igraph(nx_graph)
        ig_utils.save_ig_to_graphml(G, 'hel_ig_v1.graphml')
        G = ig_utils.read_ig_graphml('hel_ig_v1.graphml')
        for edge in G.es:
            self.assertEqual(list(edge.attributes().keys()), ['name', 'uvkey', 'length', 'noises', 'geometry', 'has_aqi'])
            self.assertEqual(len(edge.attributes().keys()), 5)
            self.assertIsInstance(edge['name'], int)
            self.assertIsInstance(edge['uvkey'], tuple)
            self.assertIsInstance(edge['length'], float)
            self.assertIsInstance(edge['noises'], dict)
            self.assertIsInstance(edge['geometry'], LineString)
            self.assertEqual(edge['has_aqi'], False)
            self.assertEqual(edge['uvkey'][0], edge.source)
            self.assertEqual(edge['uvkey'][1], edge.target)
        for vertex in G.vs:
            self.assertEqual(list(vertex.attributes().keys()), ['name', 'point'])
            self.assertEqual(len(vertex.attributes().keys()), 2)
            self.assertIsInstance(vertex['name'], int)
            self.assertIsInstance(vertex['point'], Point)

    def test_export_load_graphml(self):
        nx_graph = file_utils.load_graph_kumpula_noise()
        G = ig_utils.convert_nx_2_igraph(nx_graph)
        ig_utils.save_ig_to_graphml(G, 'kumpula_ig_v1_test.graphml')
        G = ig_utils.read_ig_graphml('kumpula_ig_v1_test.graphml')

        self.assertEqual(G.ecount(), 11931)
        for edge in G.es:
            self.assertEqual(list(edge.attributes().keys()), ['name', 'uvkey', 'length', 'noises', 'geometry', 'has_aqi'])
            self.assertIsInstance(edge['name'], int)
            self.assertIsInstance(edge['uvkey'], tuple)
            self.assertIsInstance(edge['length'], float)
            self.assertIsInstance(edge['noises'], dict)
            self.assertIsInstance(edge['geometry'], LineString)
            self.assertEqual(edge['has_aqi'], False)
            self.assertEqual(edge['uvkey'][0], edge.source)
            self.assertEqual(edge['uvkey'][1], edge.target)
        for vertex in G.vs:
            self.assertEqual(list(vertex.attributes().keys()), ['name', 'point'])
            self.assertIsInstance(vertex['name'], int)
            self.assertIsInstance(vertex['point'], Point)

    def test_get_edge_gdf(self):
        G = ig_utils.read_ig_graphml('kumpula_ig_v1_test.graphml')
        edge_gdf = ig_utils.get_edge_gdf(G, add_attrs=['length'])
        self.assertEqual(list(edge_gdf.columns), ['uvkey', 'geometry', 'length'])
        self.assertEqual(len(edge_gdf), G.ecount())

    def test_get_node_gdf(self):
        G = ig_utils.read_ig_graphml('kumpula_ig_v1_test.graphml')
        node_gdf = ig_utils.get_node_gdf(G)
        self.assertEqual(len(node_gdf), G.vcount())

# @unittest.SkipTest
class TestGraphHandler(unittest.TestCase):

    def test_get_node_by_id(self):
        self.assertIsInstance(G.get_node_by_id(0), dict)

    def test_edges_have_wgs_geoms(self):
        edge = G.get_edge_by_id(0)
        self.assertIn('geom_wgs', edge)

    def test_edges_have_noise_costs(self):
        edge = G.get_edge_by_id(0)
        self.assertIn('nc_0.5', edge)
        self.assertIn('nc_1', edge)

    def test_find_nearest_edge(self):
        point = Point(25498334.77938123, 6678297.973057264)
        edge = G.find_nearest_edge(point)
        self.assertIsInstance(edge, dict)
        self.assertEqual(edge['length'], 17.351)

    def test_find_nearest_node(self):
        point = Point(25498334.77938123, 6678297.973057264)
        node_id = G.find_nearest_node(point)
        self.assertIsInstance(node_id, int)
        self.assertGreater(node_id, 0)

    def test_get_node_geom(self):
        point = G.get_node_point_geom(0)
        self.assertIsInstance(point, Point)

    def test_get_new_node_id(self):
        new_node_id = G.get_new_node_id()
        self.assertIsInstance(new_node_id, int)
        # there should not be a node with this id yet
        node = G.get_node_by_id(new_node_id)
        self.assertEqual(node, None)

    def test_add_new_nodes(self):
        point = Point(25498334.77938123, 6678297.973057264)
        expected_new_node_id = G.get_new_node_id()
        new_node_id = G.add_new_node_to_graph(point)
        self.assertEqual(new_node_id, expected_new_node_id)
        added_node = G.get_node_by_id(new_node_id)
        self.assertEqual(added_node['name'], new_node_id)
        self.assertIsInstance(added_node['point'], Point)
        self.assertEqual(added_node['point'], point)
        # test add one more
        expected_second_new_node_id = G.get_new_node_id()
        self.assertEqual(expected_new_node_id, expected_second_new_node_id-1)
        second_new_node_id = G.add_new_node_to_graph(point)
        self.assertEqual(expected_second_new_node_id, second_new_node_id)
        second_added_node = G.get_node_by_id(second_new_node_id)
        self.assertEqual(second_added_node['name'], second_new_node_id)
    
    def test_get_new_edge_id(self):
        new_edge_id = G.get_new_edge_id()
        self.assertIsInstance(new_edge_id, int)
        # there should not be a node with this id yet
        edge = G.get_edge_by_id(new_edge_id)
        self.assertEqual(edge, None)

    def test_add_new_edge(self):
        eg_geom = G.get_edge_by_id(0)['geometry']
        expected_new_edge_id = G.get_new_edge_id()
        new_edge_id = G.add_new_edge_to_graph(0, 1, { 'geometry': eg_geom, 'length': 12.3 })
        self.assertEqual(new_edge_id, expected_new_edge_id)
        added_edge = G.get_edge_by_id(new_edge_id)
        self.assertEqual(added_edge['name'], new_edge_id )
        self.assertEqual(added_edge['length'], 12.3 )
        self.assertEqual(added_edge['geometry'], eg_geom )

    def test_find_edges_by_source_target(self):
        new_edge_id = G.add_new_edge_to_graph(1, 2, { 'length': 12.2 })
        edges = G.find_edges_between_node_pair(source=1, target=2)
        self.assertIsInstance(edges, list)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['length'], 12.2)
        # try with flipped uvkey (origin/target nodes)
        edges = G.find_edges_between_node_pair(source=2, target=1, directed=True)
        self.assertEqual(len(edges), 0)
        edges = G.find_edges_between_node_pair(source=2, target=1, directed=False)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['length'], 12.2)
        # add one more edge
        new_edge_id = G.add_new_edge_to_graph(1, 2, { 'length': 12.2 })
        edges = G.find_edges_between_node_pair(source=2, target=1, directed=False)
        self.assertEqual(len(edges), 2)
        self.assertEqual(edges[0]['length'], 12.2)

    def test_can_delete_edges(self):
        expected_node_count = G.graph.vcount()
        expected_edge_count = G.graph.ecount()
        new_node_id = G.add_new_node_to_graph(Point(25498334, 6678297))
        edge_1 = G.add_new_edge_to_graph(new_node_id, 1, { 'length': 5 })
        edge_2 = G.add_new_edge_to_graph(new_node_id, 2, { 'length': 7 })
        link_edges = { 'link1': { 'uvkey': (new_node_id, 1) } }
        # check that new edges were added
        edges_1 = G.find_edges_between_node_pair(source=new_node_id, target=1)
        edges_2 = G.find_edges_between_node_pair(source=new_node_id, target=2)
        self.assertEqual(len(edges_1), 1)
        self.assertEqual(len(edges_2), 1)
        G.delete_added_linking_edges(orig_edges=link_edges, orig_node={'node': new_node_id})
        # check that new edges were deleted
        edges_1 = G.find_edges_between_node_pair(source=new_node_id, target=1)
        edges_2 = G.find_edges_between_node_pair(source=new_node_id, target=2)
        self.assertEqual(len(edges_1), 0)
        self.assertEqual(len(edges_2), 0)
        # check that edge names still match edge indexes (mismatch would be problematic)
        for edge in G.graph.es:
            edge_attrs = edge.attributes()
            self.assertEqual(edge_attrs['name'], edge.index)
        # check that vertex names still match vertex indexes (mismatch would be problematic)
        for node in G.graph.vs:
            node_attrs = node.attributes()
            self.assertEqual(node['name'], node.index)
        # double check that edge & node counts were unchanged
        self.assertEqual(G.graph.vcount(), expected_node_count)
        self.assertEqual(G.graph.ecount(), expected_edge_count)

@unittest.SkipTest
class TestNoiseUtils(unittest.TestCase):

    def test_split_lines(self):
        split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
        count_split_lines = len(split_lines.index)
        mean_split_line_len = round(split_lines['length'].mean(),1)
        assert (count_split_lines, mean_split_line_len) == (19, 32.5)

    def test_add_noises_to_split_lines(self):
        split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
        noise_lines = noise_exps.add_noises_to_split_lines(noise_polys, split_lines)
        mean_noise =  round(noise_lines['db_lo'].mean(),1)
        min_noise = noise_lines['db_lo'].min()
        max_noise = noise_lines['db_lo'].max()
        assert (mean_noise, min_noise, max_noise) == (60.6, 45.0, 75.0)

    def test_get_exposure_lens(self):
        split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
        noise_lines = noise_exps.add_noises_to_split_lines(noise_polys, split_lines)
        noise_dict = noise_exps.get_exposures(noise_lines)
        assert noise_dict == {45: 14.356, 50: 4.96, 55: 344.866, 60: 107.11, 65: 62.58, 70: 40.678, 75: 18.673}

    def test_get_th_exposure_lens(self):
        split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
        noise_lines = noise_exps.add_noises_to_split_lines(noise_polys, split_lines)
        noise_dict = noise_exps.get_exposures(noise_lines)
        th_noise_dict = noise_exps.get_th_exposures(noise_dict, [55, 60, 65, 70])
        assert th_noise_dict == {55: 573.907, 60: 229.041, 65: 121.931, 70: 59.351}

    def test_get_noise_exposure_lines(self):
        noise_lines = noise_exps.get_noise_exposure_lines(walk_geom, noise_polys)
        mean_noise =  round(noise_lines['db_lo'].mean(),1)
        min_noise = noise_lines['db_lo'].min()
        max_noise = noise_lines['db_lo'].max()
        assert (mean_noise, min_noise, max_noise) == (59.5, 40.0, 75.0)

    def test_add_exposures_to_edges(self):
        graph_proj = files.load_graph_kumpula_noise()
        edge_dicts = graph_utils.get_all_edge_dicts(graph_proj)
        edge_gdf = graph_utils.get_edge_gdf(graph_proj, attrs=['geometry', 'length', 'uvkey'], subset=5)
        edge_gdf['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf['geometry']]
        split_lines = geom_utils.explode_lines_to_split_lines(edge_gdf, uniq_id='uvkey')
        split_line_noises = noise_exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
        edge_noises = noise_exps.aggregate_line_noises(split_line_noises, 'uvkey')
        graph_utils.update_edge_attr_to_graph(graph_proj, edge_noises, df_attr='noises', edge_attr='noises')
        edge_dicts = graph_utils.get_all_edge_dicts(graph_proj)
        edge_d = edge_dicts[0]
        print(edge_d)
        exp_len_sum = sum(edge_d['noises'].values())
        assert (edge_d['noises'], round(exp_len_sum,1)) == ({65: 107.025, 70: 20.027}, round(edge_d['length'],1))

    def test_aggregate_exposures(self):
        exp_list = [{55: 21.5, 60: 12}, {55: 3.5, 60: 1.5}, {60: 2.5, 70: 200}]
        exposure = noise_exps.aggregate_exposures(exp_list)
        print(exposure)
        assert exposure == { 55: 25, 60: 16, 70: 200 }

    def test_mean_noise_level(self):
        noises = { 55: 25, 60: 16, 70: 200 }
        mean_noise_level = noise_exps.get_mean_noise_level(noises, 300)
        assert mean_noise_level == 64.8

class TestAqiExposures(unittest.TestCase):

    def test_simple_aqi_exposure(self):
        eg_aq = 1.8
        self.assertEqual(aq_exps.get_aqi_coeff(eg_aq), 0.2)

    def test_invalid_aqi_exposure_raises(self):
        eg_aq = 0.5
        self.assertRaises(aq_exps.InvalidAqiException, aq_exps.get_aqi_coeff, eg_aq)

    def test_valid_aqi_costs(self):
        sens = [0.5, 1, 2]
        aq_costs = aq_exps.get_aqi_costs(logger, (2.0, 10.0), sens, length=10)
        self.assertDictEqual(aq_costs, { 'aqc_0.5': 11.25, 'aqc_1': 12.5, 'aqc_2': 15.0, 'has_aqi': True })

    def test_aqi_almost_1_costs(self):
        sens = [0.5, 1, 2]
        aq_costs = aq_exps.get_aqi_costs(logger, (0.98, 10.0), sens, length=10)
        self.assertDictEqual(aq_costs, { 'aqc_0.5': 10.0, 'aqc_1': 10.0, 'aqc_2': 10.0, 'has_aqi': True })

    def test_invalid_aqi_costs(self):
        sens = [0.5, 1, 2]
        aq_costs = aq_exps.get_aqi_costs(logger, (0.5, 10.0), sens, length=10)
        self.assertDictEqual(aq_costs, { 'aqc_0.5': 510.0, 'aqc_1': 1010.0, 'aqc_2': 2010.0, 'has_aqi': False })

    def test_aq_update_attrs(self):
        aqi_updater = GraphAqiUpdater(logger, G, start=False)
        aqi_exp = (0.0, 10.0)
        aq_costs = aqi_updater.get_aq_update_attrs(aqi_exp)
        self.assertEqual(aq_costs['aqc_1'], 1010.0)
        self.assertEqual(aq_costs['has_aqi'], False)
        aqi_exp = (1.0, 10.0)
        aq_costs = aqi_updater.get_aq_update_attrs(aqi_exp)
        self.assertEqual(aq_costs['aqc_1'], 10.0)
        self.assertEqual(aq_costs['has_aqi'], True)
        aqi_exp = (2.0, 10.0)
        aq_costs = aqi_updater.get_aq_update_attrs(aqi_exp)
        self.assertEqual(aq_costs['aqc_1'], 12.5)
        self.assertEqual(aq_costs['has_aqi'], True)
    
    def test_aqi_attrs(self):
        aqi_exp_list = [ (1.5, 3), (1.25, 5), (2.5, 10), (3.5, 2) ]
        aqi_attrs = PathAqiAttrs('clean', aqi_exp_list)
        aqi_attrs.set_aqi_stats(3 + 5 + 10 + 2)
        self.assertAlmostEqual(aqi_attrs.aqi_m, 2.14, places=2)
        self.assertAlmostEqual(aqi_attrs.aqc, 5.69, places=2)
        self.assertAlmostEqual(aqi_attrs.aqc_norm, 0.28, places=2)
        aqi_class_pcts_sum = sum(aqi_attrs.aqi_pcts.values())
        self.assertAlmostEqual(aqi_class_pcts_sum, 100)
        self.assertEqual(len(aqi_attrs.aqi_pcts.keys()), 3)

    def test_aqi_diff_attrs(self):
        aqi_exp_list = [ (1.5, 3), (1.25, 5), (2.5, 10), (3.5, 2) ]
        aqi_attrs = PathAqiAttrs('clean', aqi_exp_list)
        aqi_attrs.set_aqi_stats(3 + 5 + 10 + 2)
        s_path_aqi_exp_list = [ (2.5, 1), (2.25, 5), (3.5, 10), (4.5, 2) ]
        s_path_aqi_attrs = PathAqiAttrs('clean', s_path_aqi_exp_list)
        s_path_aqi_attrs.set_aqi_stats(3 + 5 + 10 + 2)
        aqi_attrs.set_aqi_diff_attrs(s_path_aqi_attrs, len_diff=2)
        self.assertAlmostEqual(aqi_attrs.aqi_m_diff, -1.07, places=2)
        self.assertAlmostEqual(aqi_attrs.aqc_diff, -4.25, places=2)
        self.assertAlmostEqual(aqi_attrs.aqc_diff_rat, -42.8, places=2)
        self.assertAlmostEqual(aqi_attrs.aqc_diff_score, 2.1, places=2)

if __name__ == '__main__':
    unittest.main()
