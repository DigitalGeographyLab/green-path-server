from typing import List, Set, Dict, Tuple
from datetime import datetime
from shapely.ops import nearest_points
from shapely.geometry import Point, LineString
import time
import ast
import pandas as pd
import geopandas as gpd
import networkx as nx
import utils.files as file_utils
import utils.noise_exposures as noise_exps
import utils.aq_exposures as aq_exps
import utils.graphs as graph_utils
import utils.igraphs as ig_utils
import utils.geometry as geom_utils
import utils.utils as utils
from utils.logger import Logger

class GraphHandler:
    """Graph handler holds a NetworkX graph object and related features (e.g. graph edges as a GeoDataFrame).

    Graph handler can be initialized after starting the green paths app. It provides functions for accessing and 
    manipulating graph during least cost path optimization. Also, it is needed by aqi_processor_app to spatially join AQI to edges.
    
    Note: 
        All utils for manipulating a graph in constructing and initializing a graph are provided by utils/graphs.py.

    Attributes:
        graph: A NetworkX graph object.
        edge_gdf: The edges of the graph as a GeoDataFrame.
        edges_sind: Spatial index of the edges GeoDataFrame.
        node_gdf: The nodes of the graph as a GeoDataFrame.
        nodes_sind: Spatial index of the nodes GeoDataFrame.

    Todo:
        * Try python-igraph (or other faster) library.
        * Calculate and update AQI costs to graph.
    """

    def __init__(self, logger: Logger, subset: bool = False, add_wgs_geom: bool = True, add_wgs_center: bool = False, set_noise_costs: bool = False):
        """Initializes a graph (and related features) used by green_paths_app and aqi_processor_app.

        Args:
            subset: A boolean variable indicating whether a subset of the graph should be loaded (subset is for testing / developing).
            add_wgs_geom: A boolean variable indicating whether wgs geoms should be added to the edges' attributes.
            add_wgs_center: A boolean variable indicating whether a wgs center point geom should be added to edge_gdf as a new column.
            set_noise_costs: A boolean variable indicating whether noise costs should be calculated and updated to the graph.
        """
        self.log = logger
        start_time = time.time()
        if (subset == True): self.graph = ig_utils.read_ig_graphml('ig_export_test.graphml')
        else: self.graph = file_utils.load_graph_full_noise()
        self.log.info('graph of '+ str(self.graph.ecount()) + ' edges read, subset: '+ str(subset))
        self.edge_gdf = ig_utils.get_edge_gdf(self.graph)
        self.edges_sind = self.edge_gdf.sindex
        self.log.debug('graph edges collected')
        self.node_gdf = ig_utils.get_node_gdf(self.graph)
        self.nodes_sind = self.node_gdf.sindex
        self.log.debug('graph nodes collected')
        self.set_edge_wgs_geoms(add_wgs_geom=add_wgs_geom, add_wgs_center=add_wgs_center)
        self.log.info('projected edges to wgs')
        self.db_costs: dict = None
        if (set_noise_costs == True): 
            self.db_costs = noise_exps.get_db_costs(version=3)
            self.set_noise_costs_to_edges()
        self.log.duration(start_time, 'graph initialized', log_level='info')
    
    def set_edge_wgs_geoms(self, add_wgs_geom: bool, add_wgs_center: bool):
        edge_updates = self.edge_gdf.copy()
        edge_updates = edge_updates.to_crs(epsg=4326)
        if (add_wgs_geom == True):
            self.update_edge_attr_to_graph(edge_gdf=edge_updates, df_attr='geometry', edge_attr='geom_wgs')
        if (add_wgs_center == True):
            # add wgs point geom of center points of the edges for joining AQI
            self.edge_gdf['center_wgs'] = [geom_utils.get_line_middle_point(line) for line in edge_updates['geometry']]

    def set_noise_costs_to_edges(self):
        """Updates all noise cost attributes to a graph.
        """
        sens = noise_exps.get_noise_sensitivities()

        for edge in self.graph.es:
            edge_attrs = edge.attributes()
            for sen in sens:
                cost_attr = 'nc_'+str(sen)
                noise_cost = noise_exps.get_noise_cost(noises=edge_attrs['noises'], db_costs=self.db_costs, sen=sen)
                self.graph.es[edge.index][cost_attr] = round(edge_attrs['length'] + noise_cost, 2)

    def update_edge_attr_to_graph(self, edge_gdf = None, from_dict: bool = False, df_attr: str = None, edge_attr: str = None):
        """Updates the given edge attribute from a DataFrame to a graph. 

        Args:
            from_dict: A boolean variable indicating whether the provided df_attr column refers to a dictionary that contains
                both names and values for the edge attributes to be set. If this is given, df_attr and edge_attr are not used.
            df_attr: The name of the column in [edge_df] from which the values for the new edge attribute are read. 
            edge_attr: A name for the edge attribute to which the new attribute values are set.
        """
        if (edge_gdf is None):
            edge_gdf = self.edge_gdf
        for edge in edge_gdf.itertuples():
            update = getattr(edge, df_attr)
            if (from_dict == False):
                self.graph.es[getattr(edge, 'Index')][edge_attr] = update
            else:
                for key in update.keys():
                    self.graph.es[getattr(edge, 'Index')][key] = update[key]

    def find_nearest_node(self, point: Point) -> int:
        """Finds the nearest node to a given point.

        Args:
            point: A point location as Shapely Point object.
        Note:
            Point should be in projected coordinate system (EPSG:3879).
        Returns:
            The name of the nearest node (number). None if no nearest node is found.
        """
        start_time = time.time()
        for radius in [100, 300, 700]:
            possible_matches_index = list(self.node_gdf.sindex.intersection(point.buffer(radius).bounds))
            if (len(possible_matches_index) == 0):
                continue
        if (len(possible_matches_index) == 0):
            self.log.warning('no near node found')
            return None
        possible_matches = self.node_gdf.iloc[possible_matches_index]
        points_union = possible_matches.geometry.unary_union
        nearest_geom = nearest_points(point, points_union)[1]
        nearest = possible_matches.geometry.geom_equals(nearest_geom)
        nearest_point =  possible_matches.loc[nearest]
        nearest_node_id = nearest_point.index.tolist()[0]
        self.log.duration(start_time, 'found nearest node', unit='ms')
        return nearest_node_id

    def get_node_by_id(self, node_id: int) -> dict:
        try:
            return self.graph.vs[node_id].attributes()
        except Exception:
            self.log.warning('could not find node by id: '+ str(node_id))
            return None

    def get_edge_by_id(self, edge_id: int) -> dict:
        try:
            return self.graph.es[edge_id].attributes()
        except Exception:
            self.log.warning('could not find edge by id: '+ str(edge_id))
            return None
    
    def get_node_point_geom(self, node_id: int) -> Point:
        node_d = self.get_node_by_id(node_id)
        return Point(node_d['x_coord'], node_d['y_coord'])

    def find_nearest_edge(self, point: Point) -> Dict:
        """Finds the nearest edge to a given point.

        Args:
            point: A point location as Shapely Point object.
        Note:
            Point should be in projected coordinate system (EPSG:3879).
        Returns:
            The nearest edge as dictionary, having key-value pairs by the columns of the edge_gdf.
            None if no nearest edge is found.
        """
        start_time = time.time()
        for radius in [80, 150, 250, 350, 650]:
            possible_matches_index = list(self.edge_gdf.sindex.intersection(point.buffer(radius).bounds))
            if (len(possible_matches_index) > 0):
                possible_matches = self.edge_gdf.iloc[possible_matches_index].copy()
                possible_matches['distance'] = [geom.distance(point) for geom in possible_matches['geometry']]
                shortest_dist = possible_matches['distance'].min()
                if (shortest_dist < radius):
                    break
        if (len(possible_matches_index) == 0):
            self.log.error('no near edges found')
            return None
        nearest = possible_matches['distance'] == shortest_dist
        self.log.duration(start_time, 'found nearest edge', unit='ms')
        edge_id = possible_matches.loc[nearest].index[0]
        return self.get_edge_by_id(edge_id)

    def get_edges_from_nodelist(self, path: List[int], cost_attr: str) -> List[dict]:
        """Loads edges from graph by ordered list of nodes representing a path.
        Loads edge attributes 'length', 'noises', 'dBrange' and 'coords'.
        """
        path_edges = []
        for idx in range(0, len(path)):
            if (idx == len(path)-1):
                break
            edge_d = {}
            node_1 = path[idx]
            node_1_point = self.get_node_point_geom(node_1)
            node_2 = path[idx+1]
            edges = self.graph[node_1][node_2]
            edge = graph_utils.get_least_cost_edge(edges, cost_attr)
            edge_d['length'] = edge['length'] if ('length' in edge) else 0.0
            edge_d['aqi_exp'] = edge['aqi_exp'] if ('aqi_exp' in edge) else None
            edge_d['aqi_cl'] = aq_exps.get_aqi_class(edge['aqi_exp'][0]) if ('aqi_exp' in edge) else None
            edge_d['noises'] = edge['noises'] if ('noises' in edge) else {}
            mdB = noise_exps.get_mean_noise_level(edge_d['noises'], edge_d['length'])
            edge_d['dBrange'] = noise_exps.get_noise_range(mdB)
            bool_flip_geom = geom_utils.bool_line_starts_at_point(node_1_point, edge['geometry'])
            edge_d['coords'] = edge['geometry'].coords if bool_flip_geom else edge['geometry'].coords[::-1]
            edge_d['coords_wgs'] = edge['geom_wgs'].coords if bool_flip_geom else edge['geom_wgs'].coords[::-1]
            path_edges.append(edge_d)
        return path_edges

    def get_new_node_id(self) -> int:
        """Returns an unique node id that can be used in creating a new node to a graph.
        """
        return max(self.graph.nodes)+1

    def get_new_node_attrs(self, point: Point) -> dict:
        """Returns the basic attributes for a new node based on a specified location (Point).
        """
        new_node_id = self.get_new_node_id()
        wgs_point = geom_utils.project_geom(point, from_epsg=3879, to_epsg=4326)
        geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
        return { 'id': new_node_id, **geom_attrs }

    def add_new_node_to_graph(self, point: Point) -> int:
        """Adds a new node to a graph at a specified location (Point) and returns the id of the new node.
        """
        attrs = self.get_new_node_attrs(point)
        self.graph.add_node(attrs['id'], ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
        return attrs['id']

    def create_linking_edges_for_new_node(self, new_node: int, split_point: Point, edge: dict, sens: list, db_costs: dict) -> dict:
        """Creates new edges from a new node that connect the node to the existing nodes in the graph. Also estimates and sets the edge cost attributes
        for the new edges based on attributes of the original edge on which the new node was added. 

        Returns:
            A dictionary containing the following keys:
            node_from: int
            new_node: int
            node_to: int
            link1_d: A dict cotaining the basic edge attributes of the first new linking edge.
            link2_d: A dict cotaining the basic edge attributes of the second new linking edge.
        """
        start_time = time.time()
        node_from = edge['uvkey'][0]
        node_to = edge['uvkey'][1]
        node_from_p = self.get_node_point_geom(node_from)
        node_to_p = self.get_node_point_geom( node_to)
        link1, link2 = geom_utils.split_line_at_point(node_from_p, node_to_p, edge['geometry'], split_point)

        # set geometry attributes for links
        link1_geom_attrs = { 'geometry': link1, 'length': round(link1.length, 2), 'geom_wgs': geom_utils.project_geom(link1, from_epsg=3879, to_epsg=4326) }
        link2_geom_attrs = { 'geometry': link2, 'length': round(link2.length, 2), 'geom_wgs': geom_utils.project_geom(link2, from_epsg=3879, to_epsg=4326) }
        # calculate & add noise cost attributes for new linking edges
        link1_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link1)
        link2_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link2)
        # calculate & add aq cost attributes for new linking edges 
        link1_aqi_cost_attrs = aq_exps.get_link_edge_aqi_cost_estimates(sens, self.log, edge_dict=edge, link_geom=link1)
        link2_aqi_cost_attrs = aq_exps.get_link_edge_aqi_cost_estimates(sens, self.log, edge_dict=edge, link_geom=link2)
        # combine link attributes to prepare adding them as new edges
        link1_attrs = { **link1_geom_attrs, **link1_noise_cost_attrs, **link1_aqi_cost_attrs }
        link2_attrs = { **link2_geom_attrs, **link2_noise_cost_attrs, **link2_aqi_cost_attrs }
        # add linking edges with noise cost attributes to graph
        self.graph.add_edges_from([ (node_from, new_node, { 'uvkey': (node_from, new_node), **link1_attrs }) ])
        self.graph.add_edges_from([ (new_node, node_from, { 'uvkey': (new_node, node_from), **link1_attrs }) ])
        self.graph.add_edges_from([ (node_to, new_node, { 'uvkey': (node_to, new_node), **link2_attrs }) ])
        self.graph.add_edges_from([ (new_node, node_to, { 'uvkey': (new_node, node_to), **link2_attrs }) ])
        link1_d = { 'uvkey': (new_node, node_from), **link1_attrs }
        link2_d = { 'uvkey': (node_to, new_node), **link2_attrs }
        self.log.duration(start_time, 'added links for new node', unit='ms')
        return { 'node_from': node_from, 'new_node': new_node, 'node_to': node_to, 'link1': link1_d, 'link2': link2_d }

    def get_least_cost_path(self, orig_node: int, dest_node: int, weight: str = 'length') -> List[int]:
        """Calculates a least cost path by the given edge weight.

        Args:
            orig_node: The name of the origin node (number).
            dest_node: The name of the destination node (number).
            weight: The name of the edge attribute to use as cost in the least cost path optimization.
        Returns:
            The least cost path as a sequence of nodes (node ids).
            Returns None if the origin and destination nodes are the same or no path is found between them.
        """
        if (orig_node != dest_node):
            try:
                s_path = nx.shortest_path(self.graph, source=orig_node, target=dest_node, weight=weight)
                return s_path
            except:
                raise Exception('Could not find paths')
        else:
            raise Exception('Origin and destination are the same location')

    def remove_new_node_and_link_edges(self, new_node: dict = None, link_edges: dict = None):
        """Removes linking edges from a graph. Needed after routing in order to keep the graph unchanged.
        """
        if (link_edges is not None):
            removed_count = 0
            removed_node = False
            # collect edges to remove as list of tuples
            rm_edges = [
                (link_edges['node_from'], link_edges['new_node']),
                (link_edges['new_node'], link_edges['node_from']),
                (link_edges['new_node'], link_edges['node_to']),
                (link_edges['node_to'], link_edges['new_node'])
                ]
            # try removing edges from graph
            for rm_edge in rm_edges:
                try:
                    self.graph.remove_edge(*rm_edge)
                    removed_count += 1
                except Exception:
                    continue
            try:
                self.graph.remove_node(new_node['node'])
                removed_node = True
            except Exception:
                pass
            if (removed_count == 0): self.log.error('Could not remove linking edges')
            if (removed_node == False): self.log.error('Could not remove new node')
