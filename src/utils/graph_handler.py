from typing import List, Set, Dict, Tuple
from shapely.ops import nearest_points
from shapely.geometry import Point, LineString
import time
from utils.schema import Edge as E, Node as N
import utils.noise_exposures as noise_exps
import utils.aq_exposures as aq_exps
import utils.igraphs as ig_utils
import utils.geometry as geom_utils
from utils.logger import Logger

class GraphHandler:
    """Graph handler holds a NetworkX graph object and related features (e.g. graph edges as a GeoDataFrame).

    Graph handler can be initialized after starting the green paths app. It provides functions for accessing and 
    manipulating graph during least cost path optimization. Also, it is needed by aqi_processor_app to spatially join AQI to edges.
    
    Note: 
        All utils for manipulating a graph in constructing and initializing a graph are provided by utils/graphs.py.

    Attributes:
        graph: An igraph graph object.
        edge_gdf: The edges of the graph as a GeoDataFrame.
        edges_sind: Spatial index of the edges GeoDataFrame.
        node_gdf: The nodes of the graph as a GeoDataFrame.
        nodes_sind: Spatial index of the nodes GeoDataFrame.

    Todo:
        * Try python-igraph (or other faster) library.
        * Calculate and update AQI costs to graph.
    """

    def __init__(self, logger: Logger, subset: bool = False, gdf_attrs: list = []):
        """Initializes a graph (and related features) used by green_paths_app and aqi_processor_app.

        Args:
            subset: A boolean variable indicating whether a subset of the graph should be loaded (subset is for testing / developing).
        """
        self.log = logger
        self.log.info('graph subset: '+ str(subset))
        start_time = time.time()
        if (subset == True): self.graph = ig_utils.read_graphml('graphs/kumpula_noises_final.graphml')
        else: self.graph = ig_utils.read_ig_graphml('hel_ig_v1.graphml')
        self.ecount = self.graph.ecount()
        self.vcount = self.graph.vcount()
        self.log.info('graph of '+ str(self.graph.ecount()) + ' edges read')
        self.edge_gdf = ig_utils.get_edge_gdf(self.graph, attrs=[])
        self.edges_sind = self.edge_gdf.sindex
        self.log.debug('graph edges collected')
        self.node_gdf = ig_utils.get_node_gdf(self.graph)
        self.nodes_sind = self.node_gdf.sindex
        self.log.debug('graph nodes collected')
        self.db_costs = noise_exps.get_db_costs(version=3)
        self.set_noise_costs_to_edges()
        self.graph.es[E.aqi_exp.value] = None # set default aqi exposure value to None
        self.log.duration(start_time, 'graph initialized', log_level='info')

    def set_noise_costs_to_edges(self):
        """Updates all noise cost attributes to a graph.
        """
        sens = noise_exps.get_noise_sensitivities()
        for edge in self.graph.es:
            # first add estimated exposure to noise level of 40 dB to edge attrs
            edge_attrs = edge.attributes()
            noises = edge_attrs[E.noises.value]
            if (noises != None):
                db_40_exp = noise_exps.estimate_db_40_exp(edge_attrs[E.noises.value], edge_attrs[E.length.value])
                if (db_40_exp > 0.0):
                    noises[40] = db_40_exp
                self.graph.es[edge.index][E.noises.value] = noises
            
            # then calculate and update noise costs to edges
            for sen, cost_attr in [(sen, 'nc_'+ str(sen)) for sen in sens]: # iterate dict of noise sensitivities and respective cost attribute names
                if (noises == None and isinstance(edge_attrs[E.geometry.value], LineString)):
                    # these are edges outside the extent of the noise data (having valid geometry)
                    # -> set high noise costs to avoid them in finding quiet paths
                    noise_cost = edge_attrs[E.length.value] * 20
                elif (not isinstance(edge_attrs[E.geometry.value], LineString)):
                    # set noise cost 0 to all edges without geometry
                    noise_cost = 0.0
                else:
                    noise_cost = noise_exps.get_noise_cost(noises=edge_attrs[E.noises.value], db_costs=self.db_costs, sen=sen)
                self.graph.es[edge.index][cost_attr] = round(edge_attrs[E.length.value] + noise_cost, 2)

    def update_edge_attr_to_graph(self, edge_gdf, df_attr: str = None):
        """Updates the given edge attribute from a DataFrame to a graph. 
        """
        for edge in edge_gdf.itertuples():
            updates: dict = getattr(edge, df_attr)
            for key in updates.keys():
                self.graph.es[getattr(edge, 'Index')][key] = updates[key]

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
            if (len(possible_matches_index) > 0):
                break
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
        return self.get_node_by_id(node_id)[N.geometry.value]

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
                possible_matches['distance'] = [geom.distance(point) for geom in possible_matches[E.geometry.name]]
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

    def get_edges_from_edge_ids(self, edge_ids: List[int]) -> List[dict]:
        """Loads edges from graph by ordered list of nodes representing a path.
        Loads edge attributes 'length', 'noises', 'dBrange' and 'coords'.
        """
        path_edges = []
        for edge_id in edge_ids:
            edge = self.get_edge_by_id(edge_id)
            # omit edges with null geometry
            if (not isinstance(edge[E.geometry.value], LineString)):
                continue
            edge_d = {}
            edge_d['length'] = edge[E.length.value]
            edge_d['aqi_exp'] = edge['aqi_exp'] if ('aqi_exp' in edge) else None
            edge_d['aqi_cl'] = aq_exps.get_aqi_class(edge['aqi_exp'][0]) if ('aqi_exp' in edge) else None
            edge_d['noises'] = edge[E.noises.value]
            mean_db = noise_exps.get_mean_noise_level(edge_d['noises'], edge_d['length']) if (edge[E.noises.value] != None) else 0
            edge_d['dBrange'] = noise_exps.get_noise_range(mean_db)
            edge_d['coords'] = edge[E.geometry.value].coords
            edge_d['coords_wgs'] = edge[E.geom_wgs.value].coords
            path_edges.append(edge_d)
        return path_edges

    def get_new_node_id(self) -> int:
        """Returns an unique node id that can be used in creating a new node to a graph.
        """
        return self.graph.vcount()

    def add_new_node_to_graph(self, point: Point) -> int:
        """Adds a new node to a graph at a specified location (Point) and returns the id of the new node.
        """
        new_node_id = self.get_new_node_id()
        attrs = { N.geometry.value: point }
        self.graph.add_vertex(**attrs)
        return new_node_id

    def get_new_edge_id(self) -> int:
        return self.graph.ecount()

    def add_new_edge_to_graph(self, source: int, target: int, attrs: dict = {}) -> int:
        new_edge_id = self.get_new_edge_id()
        self.graph.add_edge(source, target, **attrs)
        return new_edge_id

    def create_linking_edges_for_new_node(self, new_node: int, split_point: Point, edge: dict, aq_sens: list, noise_sens: list, db_costs: dict) -> dict:
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
        node_from = edge[E.uv.value][0]
        node_to = edge[E.uv.value][1]
        node_from_p = self.get_node_point_geom(node_from)
        node_to_p = self.get_node_point_geom(node_to)

        # create link geometries from/to new node in projected and WGS CRS
        link1, link2 = geom_utils.split_line_at_point(node_from_p, node_to_p, edge[E.geometry.value], split_point)
        link1_wgs, link2_wgs = tuple(geom_utils.project_geom(link, geom_epsg=3879, to_epsg=4326) for link in (link1, link2))
        link1_rev, link2_rev = tuple(LineString(link.coords[::-1]) for link in (link1, link2))
        link1_rev_wgs, link2_rev_wgs = tuple(LineString(link_wgs.coords[::-1]) for link_wgs in (link1_wgs, link2_wgs))

        # set geometry attributes for links
        link1_geom_attrs = { E.geometry.value: link1, E.length.value: round(link1.length, 2), E.geom_wgs.value: link1_wgs }
        link1_rev_geom_attrs = { E.geometry.value: link1_rev, E.length.value: round(link1.length, 2), E.geom_wgs.value: link1_rev_wgs }
        link2_geom_attrs = { E.geometry.value: link2, E.length.value: round(link2.length, 2), E.geom_wgs.value: link2_wgs }
        link2_rev_geom_attrs = { E.geometry.value: link2_rev, E.length.value: round(link2.length, 2), E.geom_wgs.value: link2_rev_wgs }
        # calculate & add noise cost attributes for new linking edges
        link1_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(noise_sens, db_costs, edge_dict=edge, link_geom=link1)
        link2_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(noise_sens, db_costs, edge_dict=edge, link_geom=link2)
        # calculate & add aq cost attributes for new linking edges 
        link1_aqi_cost_attrs = aq_exps.get_link_edge_aqi_cost_estimates(aq_sens, self.log, edge_dict=edge, link_geom=link1)
        link2_aqi_cost_attrs = aq_exps.get_link_edge_aqi_cost_estimates(aq_sens, self.log, edge_dict=edge, link_geom=link2)
        # combine link attributes to prepare adding them as new edges
        link1_attrs = { **link1_noise_cost_attrs, **link1_aqi_cost_attrs }
        link2_attrs = { **link2_noise_cost_attrs, **link2_aqi_cost_attrs }
        # add linking edges with noise cost attributes to graph
        self.add_new_edge_to_graph(node_from, new_node, { E.uv.value: (new_node, node_from), **link1_attrs, **link1_geom_attrs })
        self.add_new_edge_to_graph(new_node, node_from, { E.uv.value: (new_node, node_from), **link1_attrs, **link1_rev_geom_attrs })
        self.add_new_edge_to_graph(new_node, node_to, { E.uv.value: (new_node, node_to), **link2_attrs, **link2_geom_attrs })
        self.add_new_edge_to_graph(node_to, new_node, { E.uv.value: (new_node, node_to), **link2_attrs, **link2_rev_geom_attrs })
        link1_d = { E.uv.value: (new_node, node_from), **link1_attrs, **link1_geom_attrs }
        link2_d = { E.uv.value: (node_to, new_node), **link2_attrs, **link2_geom_attrs }
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
                s_path = self.graph.get_shortest_paths(orig_node, to=dest_node, weights=weight, mode=1, output="epath")
                return s_path[0]
            except:
                raise Exception('Could not find paths')
        else:
            raise Exception('Origin and destination are the same location')

    def delete_added_linking_edges(
        self, 
        orig_edges: dict = None,
        orig_node: dict = None, 
        dest_edges: dict = None,
        dest_node: dict = None, 
        ) -> None:
        """Deletes linking edges from a graph. Needed after routing in order to keep the graph unchanged.
        """
        delete_edge_ids = []
        delete_node_ids = []

        if (orig_edges is not None):
            delete_node_ids.append(orig_node['node'])
            try:
                # get ids of the linking edges of the origin
                from_node = orig_edges['link1'][E.uv.value][0]
                to_node = orig_edges['link1'][E.uv.value][1]
                delete_edge_ids.append(self.graph.get_eid(from_node, to_node))
                from_node = orig_edges['link2'][E.uv.value][0]
                to_node = orig_edges['link2'][E.uv.value][1]
                delete_edge_ids.append(self.graph.get_eid(from_node, to_node))
            except Exception:
                pass
        if (dest_edges is not None):
            delete_node_ids.append(dest_node['node'])
            try:
                # get ids of the linking edges of the destination
                from_node = dest_edges['link1'][E.uv.value][0]
                to_node = dest_edges['link1'][E.uv.value][1]
                delete_edge_ids.append(self.graph.get_eid(from_node, to_node))
                from_node = dest_edges['link2'][E.uv.value][0]
                to_node = dest_edges['link2'][E.uv.value][1]
                delete_edge_ids.append(self.graph.get_eid(from_node, to_node))
            except Exception:
                pass

        try:
            self.graph.delete_edges(delete_edge_ids)
            self.log.debug('deleted ' + str(len(delete_edge_ids)) + ' edges')
        except Exception:
            self.log.error('could not delete added edges from the graph')
        try:
            self.graph.delete_vertices(delete_node_ids)
            self.log.debug('deleted ' + str(len(delete_node_ids)) + ' nodes')
        except Exception:
            self.log.error('could not delete added nodes from the graph')

        # make sure that graph has the expected number of edges and nodes after routing
        if (self.graph.ecount() != self.ecount):
            self.log.error('graph has incorrect number of edges: '+ str(self.graph.ecount()) + ' is not '+ str(self.ecount))
        if (self.graph.vcount() != self.vcount):
            self.log.error('graph has incorrect number of nodes: '+ str(self.graph.vcount()) + ' is not '+ str(self.vcount))
