from typing import List, Set, Dict, Tuple
import traceback
import time
import json
import utils.noise_exposures as noise_exps 
import utils.geometry as geom_utils
import utils.utils as utils
import utils.routing as routing_utils
import utils.graphs as graph_utils
from utils.path import Path
from utils.path_set import PathSet
from utils.graph_handler import GraphHandler
from utils.logger import Logger

class PathFinder:
    """An instance of PathFinder is responsible for orchestrating all routing related tasks from finding the 
    origin & destination nodes to returning the paths as GeoJSON feature collection.
    
    Todo:
        Implement AQI based routing.
    """

    def __init__(self, logger: Logger, finder_type: str, G: GraphHandler, orig_lat, orig_lon, dest_lat, dest_lon):
        self.log = logger
        self.finder_type: str = finder_type # either 'quiet' or 'clean'
        self.G = G
        orig_latLon = {'lat': float(orig_lat), 'lon': float(orig_lon)}
        dest_latLon = {'lat': float(dest_lat), 'lon': float(dest_lon)}
        self.log.debug('initializing path finder from: '+ str(orig_latLon))
        self.log.debug('to: '+ str(dest_latLon))
        self.orig_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(orig_latLon))
        self.dest_point = geom_utils.project_geom(geom_utils.get_point_from_lat_lon(dest_latLon))
        sens_subset = self.orig_point.distance(self.dest_point) > 2000
        self.sens = noise_exps.get_noise_sensitivities(subset=sens_subset)
        self.db_costs = noise_exps.get_db_costs()
        self.PathSet = PathSet(self.log, set_type=finder_type)
        self.orig_node = None
        self.dest_node = None
        self.orig_link_edges = None
        self.dest_link_edges = None

    def find_origin_dest_nodes(self):
        """Finds & sets origin & destination nodes and linking edges as instance variables.

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        start_time = time.time()
        try:
            orig_node, dest_node, orig_link_edges, dest_link_edges = routing_utils.get_orig_dest_nodes_and_linking_edges(
                self.log, self.G, self.orig_point, self.dest_point, self.sens, self.db_costs)
            self.orig_node = orig_node
            self.dest_node = dest_node
            self.orig_link_edges = orig_link_edges
            self.dest_link_edges = dest_link_edges
            self.log.duration(start_time, 'origin & destination nodes set', unit='ms', log_level='info')
        except Exception as e:
            self.log.error('exception in finding nearest nodes:')
            traceback.print_exc()
            raise Exception(str(e))

    def find_least_cost_paths(self):
        """Finds both shortest and least cost paths. 

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        try:
            start_time = time.time()
            self.path_set = PathSet(self.log, set_type='quiet')
            shortest_path = self.G.get_least_cost_path(self.orig_node['node'], self.dest_node['node'], weight='length')
            self.path_set.set_shortest_path(Path(nodes=shortest_path, name='short_p', path_type='short', cost_attr='length'))
            for sen in self.sens:
                noise_cost_attr = 'nc_'+ str(sen)
                least_cost_path = self.G.get_least_cost_path(self.orig_node['node'], self.dest_node['node'], weight=noise_cost_attr)
                self.path_set.add_green_path(Path(nodes=least_cost_path, name='q_'+str(sen), path_type='quiet', cost_attr=noise_cost_attr, cost_coeff=sen))
            self.log.duration(start_time, 'routing done', unit='ms', log_level='info')
        except Exception:
            traceback.print_exc()
            raise Exception('Could not find paths')

    def process_paths_to_FC(self, edges: bool = True, FCs_to_files: bool = False) -> dict:
        """Loads & collects path attributes from the graph for all paths. Also aggregates and filters out nearly identical 
        paths based on geometries and length. 

        Returns:
            All paths as GeoJSON FeatureCollection (as python dictionary).
        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        start_time = time.time()
        try:
            self.path_set.set_path_edges(self.G)
            self.path_set.aggregate_path_attrs(noises=True if self.finder_type == 'quiet' else False)
            self.path_set.filter_out_unique_len_paths()
            self.path_set.set_path_noise_attrs(self.db_costs)
            self.path_set.filter_out_unique_geom_paths(buffer_m=50)
            self.path_set.set_green_path_diff_attrs()
            self.log.duration(start_time, 'aggregated paths', unit='ms')
            
            start_time = time.time()
            path_FC = self.path_set.get_paths_as_feature_collection()
            if (edges == True): 
                edge_FC = self.path_set.get_edges_as_feature_collection()
            
            self.log.duration(start_time, 'processed paths & edges to FC', unit='ms', log_level='info')

            if (FCs_to_files == True):
                with open('debug/path_fc.geojson', 'w') as outfile:
                    json.dump(path_FC, outfile, indent=3, sort_keys=True)
                if (edges == True):
                    with open('debug/edge_fc.geojson', 'w') as outfile:
                        json.dump(edge_FC, outfile, indent=3, sort_keys=True)
            
            return (path_FC, edge_FC) if (edges == True) else path_FC
        
        except Exception:
            traceback.print_exc()
            raise Exception('Error in processing paths')

    def delete_added_graph_features(self):
        """Keeps a graph clean by removing new nodes & edges created during routing from the graph.
        """
        self.log.debug('deleting created nodes & edges from the graph')
        self.G.remove_new_node_and_link_edges(new_node=self.orig_node, link_edges=self.orig_link_edges)
        self.G.remove_new_node_and_link_edges(new_node=self.dest_node, link_edges=self.dest_link_edges)
