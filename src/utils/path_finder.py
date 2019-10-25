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

class PathFinder:
    """An instance of PathFinder is responsible for orchestrating all routing related tasks from finding the 
    origin & destination nodes to returning the paths as GeoJSON feature collection.
    
    Todo:
        Implement AQI based routing.
    """

    def __init__(self, finder_type: str, G: GraphHandler, from_lat, from_lon, to_lat, to_lon, debug: bool = False):
        self.finder_type: str = finder_type # either 'quiet' or 'clean'
        self.G = G
        self.from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
        self.to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
        print('initializing path finder from', self.from_latLon, 'to', self.to_latLon)
        self.from_xy = geom_utils.get_xy_from_lat_lon(self.from_latLon)
        self.to_xy = geom_utils.get_xy_from_lat_lon(self.to_latLon)
        self.db_costs = noise_exps.get_db_costs()
        self.sens = noise_exps.get_noise_sensitivities()
        self.PathSet = PathSet(set_type=finder_type, debug_mode=debug)
        self.orig_node = None
        self.dest_node = None
        self.orig_link_edges = None
        self.dest_link_edges = None
        self.debug_mode = debug
    
    def delete_added_graph_features(self):
        """Keeps a graph clean by removing new nodes & edges created during routing from the graph.
        """
        if (self.debug_mode == True): print("deleting created nodes & edges from the graph")
        self.G.remove_new_node_and_link_edges(new_node=self.orig_node, link_edges=self.orig_link_edges)
        self.G.remove_new_node_and_link_edges(new_node=self.dest_node, link_edges=self.dest_link_edges)

    def find_origin_dest_nodes(self, debug=False):
        """Finds & sets origin & destination nodes and linking edges as instance variables.

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        start_time = time.time()
        try:
            orig_node, dest_node, orig_link_edges, dest_link_edges = routing_utils.get_orig_dest_nodes_and_linking_edges(
                self.G, self.from_xy, self.to_xy, self.sens, self.db_costs, debug=debug)
            self.orig_node = orig_node
            self.dest_node = dest_node
            self.orig_link_edges = orig_link_edges
            self.dest_link_edges = dest_link_edges
            utils.print_duration(start_time, 'origin & destination nodes set', unit='ms')
        except Exception as e:
            print('exception in finding nearest nodes:')
            traceback.print_exc()
            raise Exception(str(e))

    def find_least_cost_paths(self):
        """Finds both shortest and least cost paths. 

        Raises:
            Only meaningful exception strings that can be shown in UI.
        """
        try:
            start_time = time.time()
            self.path_set = PathSet(set_type='quiet', debug_mode=self.debug_mode)
            shortest_path = routing_utils.get_least_cost_path(self.G, self.orig_node['node'], self.dest_node['node'], weight='length')
            self.path_set.set_shortest_path(Path(nodes=shortest_path, name='short_p', path_type='short', cost_attr='length'))
            for sen in self.sens:
                noise_cost_attr = 'nc_'+ str(sen)
                least_cost_path = routing_utils.get_least_cost_path(self.G, self.orig_node['node'], self.dest_node['node'], weight=noise_cost_attr)
                self.path_set.add_green_path(Path(nodes=least_cost_path, name='q_'+str(sen), path_type='quiet', cost_attr=noise_cost_attr, cost_coeff=sen))
            utils.print_duration(start_time, 'routing done')
        except Exception:
            traceback.print_exc()
            raise Exception('Could not find paths')

    def process_paths_to_FC(self, edges: bool = False) -> dict:
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
            utils.print_duration(start_time, 'aggregated paths')
            
            start_time = time.time()
            path_FC = self.path_set.get_paths_as_feature_collection()
            utils.print_duration(start_time, 'processed paths to FC')
            
            if (edges == True):
                start_time = time.time()
                edge_FC = self.path_set.get_edges_as_feature_collection()
                utils.print_duration(start_time, 'processed edges to FC')

            if (self.debug_mode == True):
                with open('debug/path_fc.geojson', 'w') as outfile:
                    json.dump(path_FC, outfile, indent=3, sort_keys=True)
                if (edges == True):
                    with open('debug/edge_fc.geojson', 'w') as outfile:
                        json.dump(edge_FC, outfile, indent=3, sort_keys=True)
            
            return (path_FC, edge_FC) if (edges == True) else path_FC
        
        except Exception:
            traceback.print_exc()
            raise Exception('Error in processing paths')
