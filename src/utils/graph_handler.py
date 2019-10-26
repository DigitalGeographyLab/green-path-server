from typing import List, Set, Dict, Tuple
from datetime import datetime
import time
import geopandas as gpd
import networkx as nx
from shapely.ops import nearest_points
from shapely.geometry import Point, LineString
import utils.files as file_utils
import utils.noise_exposures as noise_exps
import utils.graphs as graph_utils
import utils.geometry as geom_utils
import utils.utils as utils

class GraphHandler:
    """
    Graph handler can be initialized after starting the green paths app. It provides functions for accessing and 
    manipulating graph during least cost path optimization. Note: All graph manipulation for constructing and initializing 
    a graph is provided by graph_utils (utils/graphs.py).

    Todo:
        * Add support for using other edge weights than noise (e.g. AQI)
        * Try python-igraph (or other faster) library
    """

    def __init__(self, subset: bool = False):
        """Initializes all graph related features needed in routing.
        """
        if (subset == True): self.graph = file_utils.load_graph_kumpula_noise()
        else: self.graph = file_utils.load_graph_full_noise()
        print('graph of', self.graph.size(), 'edges read, subset:', subset)
        self.edge_gdf = graph_utils.get_edge_gdf(self.graph, attrs=['geometry', 'length', 'noises'])
        self.edges_sind = self.edge_gdf.sindex
        print('graph edges collected')
        self.node_gdf = self.get_node_gdf()
        self.nodes_sind = self.node_gdf.sindex
        print('graph nodes collected')
    
    def get_node_gdf(self) -> gpd.GeoDataFrame:
        """Collects and sets the nodes of a graph as a GeoDataFrame. 
        Names of the nodes are set as the row ids in the GeoDataFrame.
        """
        nodes, data = zip(*self.graph.nodes(data=True))
        gdf_nodes = gpd.GeoDataFrame(list(data), index=nodes)
        gdf_nodes['geometry'] = gdf_nodes.apply(lambda row: Point(row['x'], row['y']), axis=1)
        gdf_nodes.crs = self.graph.graph['crs']
        gdf_nodes.gdf_name = '{}_nodes'.format(self.graph.graph['name'])
        return gdf_nodes[['geometry']]

    def set_noise_costs_to_edges(self):
        """Updates all noise cost attributes to a graph.

        Args:
            db_cost: A dictionary containing the dB-specific noise cost coefficients.
            sens: A list of sensitivity values.
            edge_gdf: A GeoDataFrame containing at least columns 'uvkey' (tuple) and 'noises' (dict).
        """
        sens = noise_exps.get_noise_sensitivities()
        db_costs = noise_exps.get_db_costs()
        edge_updates = self.edge_gdf.copy()
        for sen in sens:
            cost_attr = 'nc_'+str(sen)
            edge_updates['noise_cost'] = [noise_exps.get_noise_cost(noises=noises, db_costs=db_costs, sen=sen) for noises in edge_updates['noises']]
            edge_updates['n_cost'] = edge_updates.apply(lambda row: round(row['length'] + row['noise_cost'], 2), axis=1)
            self.update_edge_attr_to_graph(edge_updates, df_attr='n_cost', edge_attr=cost_attr)
        self.update_current_time_to_graph()
    
    def update_current_time_to_graph(self):
        timenow = datetime.now().strftime("%H:%M:%S")
        self.edge_gdf['updatetime'] =  timenow
        self.update_edge_attr_to_graph(self.edge_gdf, df_attr='updatetime', edge_attr='updatetime')
        print('updated graph at:', timenow)

    def update_edge_attr_to_graph(self, edge_updates, df_attr: str = None, edge_attr: str = None):
        """Updates the given edge attribute from a DataFrame to a graph. 

        Args:
            df_attr: The name of the column in [edge_df] from which the values for the new edge attribute are read. 
            edge_attr: A name for the edge attribute to which the new attribute values are set.
        """
        for edge in edge_updates.itertuples():
            nx.set_edge_attributes(self.graph, { getattr(edge, 'uvkey'): { edge_attr: getattr(edge, df_attr)}})

    def get_node_point_geom(self, node: int) -> Point:
        node_d = self.graph.nodes[node]
        return Point(node_d['x'], node_d['y'])

    def find_nearest_node(self, point: Point, debug=False) -> int:
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
            possible_matches_index = list(self.nodes_sind.intersection(point.buffer(radius).bounds))
            if (len(possible_matches_index) == 0):
                continue
        if (len(possible_matches_index) == 0):
            print('no near node found')
            return None
        possible_matches = self.node_gdf.iloc[possible_matches_index]
        points_union = possible_matches.geometry.unary_union
        nearest_geom = nearest_points(point, points_union)[1]
        nearest = possible_matches.geometry.geom_equals(nearest_geom)
        nearest_point =  possible_matches.loc[nearest]
        nearest_node = nearest_point.index.tolist()[0]
        if (debug == True): utils.print_duration(start_time, 'found nearest node', unit='ms')
        return nearest_node
    
    def find_nearest_edge(self, point: Point, debug=False) -> Dict:
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
            possible_matches_index = list(self.edges_sind.intersection(point.buffer(radius).bounds))
            if (len(possible_matches_index) > 0):
                possible_matches = self.edge_gdf.iloc[possible_matches_index].copy()
                possible_matches['distance'] = [geom.distance(point) for geom in possible_matches['geometry']]
                shortest_dist = possible_matches['distance'].min()
                if (shortest_dist < radius):
                    break
        if (len(possible_matches_index) == 0):
            print('no near edges found')
            return None
        nearest = possible_matches['distance'] == shortest_dist
        nearest_edge_dict =  possible_matches.loc[nearest].iloc[0].to_dict()
        if (debug == True): utils.print_duration(start_time, 'found nearest edge', unit='ms')
        return nearest_edge_dict

    def get_ordered_edge_line_coords(self, node_from: int, edge: dict) -> List[tuple]:
        """Returns the coordinates of the line geometry of an edge. The list of coordinates is ordered so that the 
        first point is at the same location as [node_from]. 
        """
        from_point = self.get_node_point_geom(node_from)
        edge_line = edge['geometry']
        edge_coords = edge_line.coords
        first_point = Point(edge_coords[0])
        last_point = Point(edge_coords[len(edge_coords)-1])
        if(from_point.distance(first_point) > from_point.distance(last_point)):
            return edge_coords[::-1]
        return edge_coords

    def get_least_cost_edge(self, edges: List[dict], cost_attr: str) -> dict:
        """Returns the least cost edge from a set of edges (dicts) by an edge cost attribute.
        """
        if (len(edges) == 1):
            return next(iter(edges.values()))
        s_edge = next(iter(edges.values()))
        for edge_k in edges.keys():
            if (cost_attr in edges[edge_k].keys() and cost_attr in s_edge.keys()):
                if (edges[edge_k][cost_attr] < s_edge[cost_attr]):
                    s_edge = edges[edge_k]
        return s_edge

    def get_edges_from_nodelist(self, path: List[int], cost_attr: str) -> List[dict]:
        """Loads edges from graph by ordered list of nodes representing a path.
        Loads edge attributes 'cost_update_time', 'length', 'noises', 'dBrange' and 'coords'.
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
            edge_d['cost_update_time'] = edge['updatetime'] if ('updatetime' in edge) else {}
            edge_d['length'] = edge['length'] if ('length' in edge) else 0.0
            edge_d['noises'] = edge['noises'] if ('noises' in edge) else {}
            mdB = noise_exps.get_mean_noise_level(edge_d['noises'], edge_d['length'])
            edge_d['dBrange'] = noise_exps.get_noise_range(mdB)
            bool_flip_geom = geom_utils.bool_line_starts_at_point(node_1_point, edge['geometry'])
            edge_d['coords'] = edge['geometry'].coords if bool_flip_geom else edge['geometry'].coords[::-1]
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

    def create_linking_edges_for_new_node(self, new_node: int, split_point: Point, edge: dict, sens: list, db_costs: dict, debug=False) -> dict:
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
        link1_geom_attrs = { 'geometry': link1, 'geom_wgs': geom_utils.project_geom(link1, from_epsg=3879, to_epsg=4326) }
        link2_geom_attrs = { 'geometry': link2, 'geom_wgs': geom_utils.project_geom(link2, from_epsg=3879, to_epsg=4326) }
        # interpolate noise cost attributes for new linking edges so that they work in quiet path routing
        link1_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link1)
        link2_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=edge, link_geom=link2)
        # combine link attributes to prepare adding them as new edges
        link1_attrs = { **link1_geom_attrs, **link1_cost_attrs, 'updatetime': edge['updatetime'] }
        link2_attrs = { **link2_geom_attrs, **link2_cost_attrs, 'updatetime': edge['updatetime'] }
        # add linking edges with noise cost attributes to graph
        self.graph.add_edges_from([ (node_from, new_node, { 'uvkey': (node_from, new_node), **link1_attrs }) ])
        self.graph.add_edges_from([ (new_node, node_from, { 'uvkey': (new_node, node_from), **link1_attrs }) ])
        self.graph.add_edges_from([ (node_to, new_node, { 'uvkey': (node_to, new_node), **link2_attrs }) ])
        self.graph.add_edges_from([ (new_node, node_to, { 'uvkey': (new_node, node_to), **link2_attrs }) ])
        link1_d = { 'uvkey': (new_node, node_from), **link1_attrs }
        link2_d = { 'uvkey': (node_to, new_node), **link2_attrs }
        if (debug == True): utils.print_duration(start_time, 'added links for new node', unit='ms')
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
            if (removed_count == 0): print('Could not remove linking edges')
            if (removed_node == False): print('Could not remove new node')
