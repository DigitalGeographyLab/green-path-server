import time
from typing import List, Dict, Tuple, Union
from shapely.ops import nearest_points
from shapely.geometry import Point, LineString
import gp_server.env as env
from gp_server.app.types import PathEdge 
from common.igraph import Edge as E, Node as N
import common.igraph as ig_utils
import gp_server.app.noise_exposures as noise_exps
import gp_server.app.aq_exposures as aq_exps
import gp_server.app.greenery_exposures as gvi_exps
import common.geometry as geom_utils
from gp_server.app.logger import Logger
from gp_server.app.constants import RoutingException, ErrorKeys, cost_prefix_dict, TravelMode, RoutingMode


class GraphHandler:
    """Graph handler provides functions for accessing and manipulating graph during least cost path optimization. 
    
    Attributes:
        graph: An igraph graph object.
        __edge_gdf: The edges of the graph as a GeoDataFrame.
        __edges_sind: Spatial index of the edges GeoDataFrame.
        __node_gdf: The nodes of the graph as a GeoDataFrame.
        __nodes_sind: Spatial index of the nodes GeoDataFrame.
        __db_costs: Cost coefficients for different noise levels.
        __new_edges: New edges are first collected to dictionary and then added all at once.
        __edge_cache: A cache of path edges for current routing request. 
    """

    def __init__(self, logger: Logger, graph_file: str):
        """Initializes a graph (and related features) used by green_paths_app and aqi_processor_app.

        Args:
            subset: A boolean variable indicating whether a subset of the graph should be loaded (subset is for testing / developing).
        """
        self.log = logger
        self.log.info(f'Loading graph from file: {graph_file}')
        start_time = time.time()
        self.graph = ig_utils.read_graphml(graph_file)
        self.ecount = self.graph.ecount()
        self.vcount = self.graph.vcount()
        self.log.info('Graph of '+ str(self.graph.ecount()) + ' edges read')
        self.__edge_gdf = self.__get_edge_gdf()
        self.__edge_sindex = self.__edge_gdf.sindex
        self.__node_gdf = ig_utils.get_node_gdf(self.graph)
        self.__nodes_sind = self.__node_gdf.sindex
        self.db_costs = noise_exps.get_db_costs(version=3)
        if env.quiet_paths_enabled: self.__set_noise_costs_to_edges()
        self.log.info('Noise costs set')
        if env.gvi_paths_enabled: self.__set_gvi_costs_to_graph()
        self.log.info('GVI costs set')
        self.graph.es[E.aqi.value] = None # set default AQI value to None
        self.log.duration(start_time, 'Graph initialized', log_level='info')
        self.__new_edges: Dict[Tuple[int, int], Dict] = {}
        self.__edge_cache: Dict[int, PathEdge] = {}

    def __get_edge_gdf(self):
        edge_gdf = ig_utils.get_edge_gdf(self.graph, attrs=[E.id_way])
        # drop edges with identical geometry
        edge_gdf = edge_gdf.drop_duplicates(E.id_way.name)
        # drop edges without geometry
        edge_gdf = edge_gdf[edge_gdf[E.geometry.name].apply(lambda geom: isinstance(geom, LineString))]
        edge_gdf = edge_gdf[[E.geometry.name]]
        self.log.info(f'Added {len(edge_gdf)} edges to edge_gdf')
        return edge_gdf

    def __set_noise_costs_to_edges(self):
        """Updates all noise cost attributes to a graph.
        """
        cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.QUIET]
        cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.QUIET]

        noises_list = self.graph.es[E.noises.value]
        length_list = self.graph.es[E.length.value]
        biking_length_list = self.graph.es[E.length_b.value]
        has_geom_list = [isinstance(geom, LineString) for geom in list(self.graph.es[E.geometry.value])]

        # update dB 40 lengths to graph (the lowest level in noise data is 45)
        noises_lengths = zip(noises_list, length_list)
        self.graph.es[E.noises.value] = [
            noise_exps.add_db_40_exp_to_noises(noises, length)
            for noises, length
            in noises_lengths
        ]

        for sen in noise_exps.get_noise_sensitivities():

            if env.walking_enabled:
                lengths_noises_b_geoms = zip(length_list, noises_list, has_geom_list)
                cost_attr = cost_prefix + str(sen)

                self.graph.es[cost_attr] = [
                    noise_exps.get_noise_adjusted_edge_cost(
                        sen, self.db_costs, noises, length
                    ) if has_geom else 0.0
                    for length, noises, has_geom
                    in lengths_noises_b_geoms
                ]

            if env.cycling_enabled:
                lengths_noises_b_geoms = zip(length_list, biking_length_list, noises_list, has_geom_list)
                cost_attr = cost_prefix_bike + str(sen)

                self.graph.es[cost_attr] = [
                    noise_exps.get_noise_adjusted_edge_cost(
                        sen, self.db_costs, noises, length, length_b
                    ) if has_geom else 0.0
                    for length, length_b, noises, has_geom
                    in lengths_noises_b_geoms
                ]

    def __set_gvi_costs_to_graph(self):
        cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.GREEN]
        cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.GREEN]

        lengths = self.graph.es[E.length.value]
        biking_lengths = self.graph.es[E.length_b.value]
        gvi_list = self.graph.es[E.gvi.value]
        has_geom_list = [isinstance(geom, LineString) for geom in list(self.graph.es[E.geometry.value])]

        for sen in gvi_exps.get_gvi_sensitivities():
            
            if env.walking_enabled:
                length_gvi_b_geom = zip(lengths, gvi_list, has_geom_list)
                cost_attr = cost_prefix + str(sen)
                self.graph.es[cost_attr] = [
                    gvi_exps.get_gvi_adjusted_cost(length, gvi, sen=sen) 
                    if has_geom else 0.0
                    for length, gvi, has_geom 
                    in length_gvi_b_geom
                ]

            if env.cycling_enabled:
                length_gvi_b_geom = zip(lengths, biking_lengths, gvi_list, has_geom_list)
                cost_attr = cost_prefix_bike + str(sen)
                self.graph.es[cost_attr] = [
                    gvi_exps.get_gvi_adjusted_cost(
                        length, gvi, length_b=length_b, sen=sen
                    )
                    if has_geom else 0.0
                    for length, length_b, gvi, has_geom 
                    in length_gvi_b_geom
                ]

    def update_edge_attr_to_graph(self, edge_gdf, df_attr: str):
        """Updates the given edge attribute(s) from a DataFrame to a graph. The attribute(s) to update
        are given as series of dictionaries (df_attr): keys will be used ass attribute names and values
        as values in the graph. 
        """
        for edge in edge_gdf.itertuples():
            updates: dict = getattr(edge, df_attr)
            self.graph.es[getattr(edge, E.id_ig.name)].update_attributes(updates)

    def find_nearest_node(self, point: Point) -> Union[int, None]:
        """Finds the nearest node to a given point from the graph.

        Args:
            point: A point location as Shapely Point object.
        Note:
            Point should be in projected coordinate system (EPSG:3879).
        Returns:
            The name (id) of the nearest node. None if no nearest node is found.
        """
        for radius in [50, 100, 500]:
            possible_matches_index = list(self.__node_gdf.sindex.intersection(point.buffer(radius).bounds))
            if possible_matches_index:
                break
        if not possible_matches_index:
            self.log.warning('No near node found')
            return None
        possible_matches = self.__node_gdf.iloc[possible_matches_index]
        points_union = possible_matches.geometry.unary_union
        nearest_geom = nearest_points(point, points_union)[1]
        nearest = possible_matches.geometry.geom_equals(nearest_geom)
        nearest_point =  possible_matches.loc[nearest]
        nearest_node_id = nearest_point.index.tolist()[0]
        return nearest_node_id

    def __get_node_by_id(self, node_id: int) -> Union[dict, None]:
        try:
            return self.graph.vs[node_id].attributes()
        except Exception:
            self.log.warning('Could not find node by id: '+ str(node_id))
            return None

    def get_edge_attrs_by_id(self, edge_id: int) -> Union[dict, None]:
        """Returns edge by given ID as dictionary of attribute names and values."""
        try:
            return self.graph.es[edge_id].attributes()
        except Exception:
            self.log.warning('Could not find edge by id: '+ str(edge_id))
            return None

    def get_edge_object_by_id(self, edge_id: int) -> Union[PathEdge, None]:
        """Returns PathEdge object by the given edge ID. Returns None if the edge is
        not found or it lacks geometry.
        """
        edge = self.get_edge_attrs_by_id(edge_id)
        
        if (not edge or edge[E.length.value] == 0.0 
                or not isinstance(edge[E.geometry.value], LineString)):
            return None

        return PathEdge(
            id = edge[E.id_ig.value],
            length = edge[E.length.value],
            length_b = edge[E.length_b.value] if edge[E.length_b.value] else 0,
            aqi = edge[E.aqi.value],
            aqi_cl = aq_exps.get_aqi_class(edge[E.aqi.value]) if edge[E.aqi.value] else None,
            noises = edge[E.noises.value],
            gvi = edge[E.gvi.value],
            gvi_cl = gvi_exps.get_gvi_class(
                edge[E.gvi.value]
            ) if edge[E.gvi.value] is not None else None,
            coords = edge[E.geometry.value].coords,
            coords_wgs = edge[E.geom_wgs.value].coords
        )

    def get_node_point_geom(self, node_id: int) -> Union[Point, None]:
        node = self.__get_node_by_id(node_id)
        return node[N.geometry.value] if node else None

    def find_nearest_edge(self, point: Point) -> Union[dict, None]:
        """Finds the nearest edge to a given point and returns it as dictionary of edge attributes.
        """
        for radius in [35, 150, 400, 650]:
            possible_matches_index = list(self.__edge_gdf.sindex.intersection(point.buffer(radius).bounds))
            if possible_matches_index:
                possible_matches = self.__edge_gdf.iloc[possible_matches_index].copy()
                possible_matches['distance'] = [geom.distance(point) for geom in possible_matches[E.geometry.name]]
                shortest_dist = possible_matches['distance'].min()
                if (shortest_dist < radius):
                    break
        if not possible_matches_index:
            self.log.error('No near edges found')
            return None
        nearest = possible_matches['distance'] == shortest_dist
        edge_id = possible_matches.loc[nearest].index[0]
        edge = self.get_edge_attrs_by_id(edge_id)
        edge['dist'] = round(shortest_dist, 2)
        return edge

    def format_edge_dict_for_debugging(self, edge: dict) -> dict:
        # map edge dict attribute names to the descriptive ones defined in Edge enum
        edge_d = { E(k).name if k in [item.value for item in E] else k: v for k, v in edge.items() }
        edge_d[E.geometry.name] = str(edge_d[E.geometry.name])
        edge_d[E.geom_wgs.name] = str(edge_d[E.geom_wgs.name])
        return edge_d

    def get_path_edges_by_ids(self, edge_ids: List[int]) -> List[PathEdge]:
        """Loads edge attributes from graph by ordered list of edges representing a path.
        """
        path_edges: List[PathEdge] = []
        
        for edge_id in edge_ids:
            edge_d = self.__edge_cache.get(edge_id)
            if edge_d:
                path_edges.append(edge_d)
                continue

            path_edge = self.get_edge_object_by_id(edge_id)
            
            if path_edge:
                self.__edge_cache[edge_id] = path_edge
                path_edges.append(path_edge)

        return path_edges

    def __get_new_node_id(self) -> int:
        """Returns an unique node id that can be used in creating a new node to a graph.
        """
        return self.graph.vcount()

    def add_new_node_to_graph(self, point: Point) -> int:
        """Adds a new node to a graph at a specified location (Point) and returns the id of the new node.
        """
        new_node_id = self.__get_new_node_id()
        attrs = { N.geometry.value: point }
        self.graph.add_vertex(**attrs)
        return new_node_id

    def __get_new_edge_id(self) -> int:
        return self.graph.ecount()

    def __add_new_edges_to_graph(self, edge_uvs: List[Tuple[int, int]]) -> List[int]:
        """Adds new edges to graph and returns their ids as list."""
        new_edge_id = self.__get_new_edge_id()
        self.graph.add_edges(edge_uvs)
        return [new_edge_id + edge_number for edge_number in range(0, len(edge_uvs))]

    def __get_link_edge_aqi_cost_estimates(self, edge_dict: dict, link_geom: LineString, sens) -> dict:
        """Returns aqi exposures and costs for a split edge based on aqi exposures on the original edge
        (from which the edge was split). 
        """
        cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.CLEAN]
        cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.CLEAN]

        if (edge_dict[E.aqi.value] is None):
            # the path may start from an edge without AQI, but cost attributes need to be set anyway
            return { 
                E.aqi.value: None, 
                **{cost_prefix + str(sen) : round(link_geom.length * 2, 2) for sen in sens },
                **{cost_prefix_bike + str(sen) : round(link_geom.length * 2, 2) for sen in sens }
                }
        else:
            aqi_costs = aq_exps.get_aqi_costs(edge_dict[E.aqi.value], link_geom.length, sens)
            aqi_costs_b = aq_exps.get_aqi_costs(edge_dict[E.aqi.value], link_geom.length, sens, travel_mode=TravelMode.BIKE)
            return { E.aqi.value: edge_dict[E.aqi.value], **aqi_costs, **aqi_costs_b }

    def __get_link_edge_gvi_costs(self, edge_dict: dict, link_geom: LineString, sens: List[float]):
        cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.GREEN]
        cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.GREEN]
        gvi = edge_dict[E.gvi.value] if edge_dict[E.gvi.value] is not None else 0.0
        return {
            E.gvi.value: gvi,
            **{ cost_prefix + str(sen) : gvi_exps.get_gvi_adjusted_cost(link_geom.length, gvi, sen) for sen in sens },
            **{ cost_prefix_bike + str(sen) : gvi_exps.get_gvi_adjusted_cost(link_geom.length, gvi, sen) for sen in sens }
        }

    def create_linking_edges_for_new_node(
        self, 
        new_node: int,
        split_point: Point,
        edge: dict,
        aq_sens: list,
        noise_sens: list,
        db_costs: dict,
        origin: bool
    ) -> dict:
        """Creates new edges to/from a new node to connect it to two existing nodes of the graph. 
        Also estimates and sets the edge cost attributes for the new edges based on attributes 
        of the original edge on which the new node was added. 

        Args:
            new_node: identifier of the new node.
            split_point: geometry of the new node (for splitting the underlying edge).
            edge: edge on which the new node was created.
            aq_sens: air quality sensitivities to use in calculating aq costs for new edges.
            noise_sens: noise sensitivities to use in calculating noise costs for new edges.
            db_costs: dB specific cost coefficients to use in calculating noise costs.
            origin: a boolean variable indicating whether the operation is to be done for origin (not dest.).

        Returns:
            A dictionary containing the following keys:
            node_from: int
            new_node: int
            node_to: int
            link1_d: A dict cotaining the basic edge attributes of the first new linking edge.
            link2_d: A dict cotaining the basic edge attributes of the second new linking edge.
        """
        time_func = time.time()
        node_from = edge[E.uv.value][0]
        node_to = edge[E.uv.value][1]

        # create link geometries from/to new node in projected and WGS CRS
        time_projections = time.time()
        link1, link2 = geom_utils.split_line_at_point(self.log, edge[E.geometry.value], split_point)
        link1_wgs, link2_wgs = tuple(geom_utils.project_geom(link, geom_epsg=3879, to_epsg=4326) for link in (link1, link2))
        link1_rev, link2_rev, link1_rev_wgs, link2_rev_wgs = (LineString(link.coords[::-1]) for link in (link1, link2, link1_wgs, link2_wgs))
        self.log.duration(time_projections, 'projected linking edge geoms', unit='ms')

        # set geometry attributes for links
        link1_geom_attrs = { E.geometry.value: link1, E.length.value: round(link1.length, 2), E.geom_wgs.value: link1_wgs }
        link1_rev_geom_attrs = { E.geometry.value: link1_rev, E.length.value: round(link1.length, 2), E.geom_wgs.value: link1_rev_wgs }
        link2_geom_attrs = { E.geometry.value: link2, E.length.value: round(link2.length, 2), E.geom_wgs.value: link2_wgs }
        link2_rev_geom_attrs = { E.geometry.value: link2_rev, E.length.value: round(link2.length, 2), E.geom_wgs.value: link2_rev_wgs }
        # calculate & add noise cost attributes for new linking edges
        link1_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(noise_sens, db_costs, edge_dict=edge, link_geom=link1)
        link2_noise_cost_attrs = noise_exps.get_link_edge_noise_cost_estimates(noise_sens, db_costs, edge_dict=edge, link_geom=link2)
        # calculate & add aq cost attributes for new linking edges 
        link1_aqi_cost_attrs = self.__get_link_edge_aqi_cost_estimates(edge_dict=edge, link_geom=link1, sens=aq_sens)
        link2_aqi_cost_attrs = self.__get_link_edge_aqi_cost_estimates(edge_dict=edge, link_geom=link2, sens=aq_sens)
        # set GVI attributes for linking edges TODO add GVI costs when needed
        link1_gvi_attrs = self.__get_link_edge_gvi_costs(edge, link1, gvi_exps.get_gvi_sensitivities())
        link2_gvi_attrs = self.__get_link_edge_gvi_costs(edge, link2, gvi_exps.get_gvi_sensitivities())
        # combine attributes for linking edges to one dictionary per new edge
        link1_attrs = { **link1_noise_cost_attrs, **link1_aqi_cost_attrs, **link1_gvi_attrs }
        link2_attrs = { **link2_noise_cost_attrs, **link2_aqi_cost_attrs, **link2_gvi_attrs }

        # add linking edges with noise cost attributes to graph (save for loading them to graph later)
        if origin:
            # add linking edges from new node to existing nodes
            self.__new_edges.update({
                (new_node, node_from): { E.uv.value: (new_node, node_from), **link1_attrs, **link1_rev_geom_attrs },
                (new_node, node_to): { E.uv.value: (new_node, node_to), **link2_attrs, **link2_geom_attrs },
            })
            link1_d = { E.uv.value: (new_node, node_from), **link1_attrs, **link1_rev_geom_attrs }
            link2_d = { E.uv.value: (new_node, node_to), **link2_attrs, **link2_geom_attrs }
        else:
            # add linking edges from existing nodes to new node
            self.__new_edges.update({
                (node_from, new_node): { E.uv.value: (node_from, new_node), **link1_attrs, **link1_geom_attrs },
                (node_to, new_node): { E.uv.value: (node_to, new_node), **link2_attrs, **link2_rev_geom_attrs }
            })
            link1_d = { E.uv.value: (node_from, new_node), **link1_attrs, **link1_geom_attrs }
            link2_d = { E.uv.value: (node_to, new_node), **link2_attrs, **link2_rev_geom_attrs }
        
        self.log.duration(time_func, 'created links for new node (GraphHandler function)', unit='ms')
        return { 'node_from': node_from, 'new_node': new_node, 'node_to': node_to, 'link1': link1_d, 'link2': link2_d }

    def load_new_edges_to_graph(self) -> None:
        time_add_edges = time.time()
        if self.__new_edges:
            new_edge_ids = self.__add_new_edges_to_graph(list(self.__new_edges.keys()))
            new_edge_attrs: List[dict] = list(self.__new_edges.values())
            for idx, edge_id in enumerate(new_edge_ids):
                for key, value in new_edge_attrs[idx].items():
                    self.graph.es[edge_id][key] = value

        self.__new_edges = {}
        self.log.duration(time_add_edges, 'loaded new features to graph', unit='ms')

    def get_least_cost_path(self, orig_node: int, dest_node: int, weight: str='length') -> List[int]:
        """Calculates a least cost path by the given edge weight.

        Args:
            orig_node: The name of the origin node (int).
            dest_node: The name of the destination node (int).
            weight: The name of the edge attribute to use as cost in the least cost path optimization.
        Returns:
            The least cost path as a sequence of edges (ids).
        """
        if (orig_node != dest_node):
            try:
                s_path = self.graph.get_shortest_paths(orig_node, to=dest_node, weights=weight, mode=1, output="epath")
                return s_path[0]
            except:
                raise Exception(f'Could not find paths by {weight}')
        else:
            raise RoutingException(ErrorKeys.OD_SAME_LOCATION.value)

    def reset_edge_cache(self):
        self.__edge_cache = {}

    def delete_added_linking_edges(self, 
        orig_edges: dict=None,
        orig_node: dict=None, 
        dest_edges: dict=None,
        dest_node: dict=None, 
        ) -> None:
        """Deletes linking edges from the graph. Needed after routing in order to keep the graph unchanged.
        """
        delete_node_ids = []

        if orig_edges:
            # delete node because it was not in the graph before routing
            delete_node_ids.append(orig_node['node'])
        
        if dest_edges:
            # delete node because it was not in the graph before routing
            delete_node_ids.append(dest_node['node'])

        try:
            self.graph.delete_vertices(delete_node_ids)
            self.log.debug(f'Deleted {len(delete_node_ids)} nodes')
        except Exception:
            self.log.error('Could not delete added nodes or edges from the graph')

        # make sure that graph has the expected number of edges and nodes after routing
        if (self.graph.ecount() != self.ecount):
            self.log.error('Graph has incorrect number of edges: '+ str(self.graph.ecount()) + ' is not '+ str(self.ecount))
        if (self.graph.vcount() != self.vcount):
            self.log.error('Graph has incorrect number of nodes: '+ str(self.graph.vcount()) + ' is not '+ str(self.vcount))
