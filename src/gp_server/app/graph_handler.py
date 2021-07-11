import time
from typing import List, Dict, Tuple, Union
from shapely.ops import nearest_points
from shapely.geometry import Point, LineString
from gp_server.conf import conf
from gp_server.app.types import NearestEdge, PathEdge, RoutingConf
from common.igraph import Edge as E, Node as N
import common.igraph as ig_utils
import gp_server.app.aq_exposures as aq_exps
import gp_server.app.greenery_exposures as gvi_exps
import gp_server.app.edge_cost_factory as edge_cost_factory
from gp_server.app.logger import Logger
from gp_server.app.constants import RoutingException, ErrorKey


class GraphHandler:
    """Graph handler provides functions for accessing and manipulating graph before, during
    and after least cost path optimization.

    Attributes:
        graph: An igraph graph object.
        routing_conf: A RoutingConf object.
        __edge_gdf: The edges of the graph as a GeoDataFrame.
        __edges_sind: Spatial index of the edges GeoDataFrame.
        __node_gdf: The nodes of the graph as a GeoDataFrame.
        __nodes_sind: Spatial index of the nodes GeoDataFrame.
        __path_edge_cache: A cache of path edges for current routing request.
    """

    def __init__(self, logger: Logger, graph_file: str, routing_conf: RoutingConf):
        """Initializes a graph (and related features) used by green_paths_app and aqi_processor_app.

        Args:
            subset: A boolean variable indicating whether a subset of the graph should be loaded
            (subset is for testing / developing).
        """
        self.log = logger
        self.log.info(f'Loading graph from file: {graph_file}')
        start_time = time.time()
        self.graph = ig_utils.read_graphml(graph_file)
        self.routing_conf = routing_conf
        self.ecount = self.graph.ecount()
        self.vcount = self.graph.vcount()
        self.log.info(f'Graph of {self.graph.ecount()} edges read')
        self.__edge_gdf = self.__get_edge_gdf()
        self.__edge_sindex = self.__edge_gdf.sindex
        self.__node_gdf = ig_utils.get_node_gdf(self.graph, drop_na_geoms=True)
        self.__nodes_sind = self.__node_gdf.sindex
        if conf.cycling_enabled:
            edge_cost_factory.set_biking_costs(self.graph, self.log)
        if conf.quiet_paths_enabled:
            edge_cost_factory.set_noise_costs_to_edges(self.graph, routing_conf)
        self.log.info('Noise costs set')
        if conf.gvi_paths_enabled:
            edge_cost_factory.set_gvi_costs_to_graph(self.graph, routing_conf)
        self.log.info('GVI costs set')
        self.graph.es[E.aqi.value] = None  # set default AQI value to None
        self.log.duration(start_time, 'Graph initialized', log_level='info')
        self.__path_edge_cache: Dict[int, PathEdge] = {}

    def __get_edge_gdf(self):
        edge_gdf = ig_utils.get_edge_gdf(self.graph, attrs=[E.id_way], drop_na_geoms=True)
        # drop edges with identical geometry
        edge_gdf = edge_gdf.drop_duplicates(E.id_way.name)
        edge_gdf = edge_gdf[[E.geometry.name]]
        self.log.info(f'Added {len(edge_gdf)} edges to edge_gdf')
        return edge_gdf

    def update_edge_attrs_from_df_to_graph(self, edge_gdf, df_attr: str):
        """Updates the given edge attribute(s) from a DataFrame to a graph. The attribute(s) to
        update are given as series of dictionaries (df_attr): keys will be used ass attribute names
        and values as values in the graph.
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
        for radius in (50, 100) + (conf.max_od_search_dist_m,):
            possible_matches_index = list(
                self.__node_gdf.sindex.intersection(point.buffer(radius).bounds)
            )
            if possible_matches_index:
                break
        if not possible_matches_index:
            self.log.warning('No near node found')
            return None
        possible_matches = self.__node_gdf.iloc[possible_matches_index]
        points_union = possible_matches.geometry.unary_union
        nearest_geom = nearest_points(point, points_union)[1]
        nearest = possible_matches.geometry.geom_equals(nearest_geom)
        nearest_point = possible_matches.loc[nearest]
        nearest_node_id = nearest_point.index.tolist()[0]
        return nearest_node_id

    def __get_node_by_id(self, node_id: int) -> Union[dict, None]:
        try:
            return self.graph.vs[node_id].attributes()
        except Exception:
            self.log.warning(f'Could not find node by id: {node_id}')
            return None

    def get_edge_attrs_by_id(self, edge_id: int) -> Union[dict, None]:
        """Returns edge by given ID as dictionary of attribute names and values."""
        try:
            return self.graph.es[edge_id].attributes()
        except Exception:
            self.log.warning(f'Could not find edge by id: {edge_id}')
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
            id=edge[E.id_ig.value],
            length=edge[E.length.value],
            bike_time_cost=edge.get(E.bike_time_cost.value, None),
            bike_safety_cost=edge.get(E.bike_safety_cost.value, None),
            allows_biking=edge[E.allows_biking.value],
            aqi=edge[E.aqi.value],
            aqi_cl=aq_exps.get_aqi_class(edge[E.aqi.value]) if edge[E.aqi.value] else None,
            noises=edge[E.noises.value],
            gvi=edge[E.gvi.value],
            gvi_cl=gvi_exps.get_gvi_class(
                edge[E.gvi.value]
            ) if edge[E.gvi.value] is not None else None,
            coords=edge[E.geometry.value].coords,
            coords_wgs=edge[E.geom_wgs.value].coords
        )

    def get_node_point_geom(self, node_id: int) -> Union[Point, None]:
        node = self.__get_node_by_id(node_id)
        return node[N.geometry.value] if node else None

    def find_nearest_edge(self, point: Point) -> Union[NearestEdge, None]:
        """Finds the nearest edge to a given point and returns it as dictionary of edge attributes.
        """
        for radius in (35, 150, 400) + (conf.max_od_search_dist_m,):
            possible_matches_index = list(
                self.__edge_gdf.sindex.intersection(point.buffer(radius).bounds)
            )
            if possible_matches_index:
                possible_matches = self.__edge_gdf.iloc[possible_matches_index].copy()
                possible_matches['distance'] = [
                    geom.distance(point) for geom in possible_matches[E.geometry.name]
                ]
                shortest_dist = possible_matches['distance'].min()
                if shortest_dist < radius:
                    break
        if not possible_matches_index:
            self.log.error('No near edges found')
            return None
        nearest = possible_matches['distance'] == shortest_dist
        edge_id = possible_matches.loc[nearest].index[0]
        attrs = self.get_edge_attrs_by_id(edge_id)
        return NearestEdge(attrs, round(shortest_dist, 2))

    def format_edge_dict_for_debugging(self, edge: dict) -> dict:
        # map edge dict attribute names to the descriptive ones defined in Edge enum
        edge_d = {E(k).name if k in [item.value for item in E] else k: v for k, v in edge.items()}
        edge_d[E.geometry.name] = str(edge_d[E.geometry.name])
        edge_d[E.geom_wgs.name] = str(edge_d[E.geom_wgs.name])
        return edge_d

    def get_path_edges_by_ids(self, edge_ids: List[int]) -> List[PathEdge]:
        """Loads edge attributes from graph by ordered list of edges representing a path.
        """
        path_edges: List[PathEdge] = []

        for edge_id in edge_ids:
            edge_d = self.__path_edge_cache.get(edge_id)
            if edge_d:
                path_edges.append(edge_d)
                continue

            path_edge = self.get_edge_object_by_id(edge_id)

            if path_edge:
                self.__path_edge_cache[edge_id] = path_edge
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
        attrs = {N.geometry.value: point}
        self.graph.add_vertex(**attrs)
        return new_node_id

    def __get_new_edge_id(self) -> int:
        return self.graph.ecount()

    def __add_new_edges_to_graph(self, edge_uvs: Tuple[Tuple[int, int]]) -> Tuple[int]:
        """Adds new edges to graph and returns their ids as list."""
        next_new_edge_id = self.__get_new_edge_id()
        self.graph.add_edges(edge_uvs)
        return tuple(
            next_new_edge_id + edge_number for edge_number in range(0, len(edge_uvs))
        )

    def add_new_edges_to_graph(self, edges: Tuple[dict]) -> None:
        time_add_edges = time.time()
        if edges:
            uvs = tuple(edge[E.uv.value] for edge in edges)
            new_edge_ids = self.__add_new_edges_to_graph(uvs)
            for idx, edge_id in enumerate(new_edge_ids):
                self.graph.es[edge_id].update_attributes(edges[idx])

        self.log.duration(time_add_edges, 'loaded new features to graph', unit='ms')

    def get_least_cost_path(
        self,
        orig_node: int,
        dest_node: int,
        weight: str = 'length'
    ) -> List[int]:
        """Calculates a least cost path by the given edge weight.

        Args:
            orig_node: The name of the origin node (int).
            dest_node: The name of the destination node (int).
            weight: The name of the edge attribute to use as cost in the least cost path
                optimization.
        Returns:
            The least cost path as a sequence of edges (ids).
        """
        if orig_node != dest_node:
            try:
                s_path = self.graph.get_shortest_paths(
                    orig_node,
                    to=dest_node,
                    weights=weight,
                    mode=1,
                    output='epath'
                )
                return s_path[0]
            except Exception:
                raise Exception(f'Could not find paths by {weight}')
        else:
            raise RoutingException(ErrorKey.OD_SAME_LOCATION.value)

    def reset_edge_cache(self):
        self.__path_edge_cache = {}

    def drop_nodes_edges(self, node_ids=Tuple) -> None:
        """Removes nodes and connected edges from the graph.
        """
        try:
            self.graph.delete_vertices(node_ids)
            self.log.debug(f'Removed {len(node_ids)} nodes')
        except Exception:
            self.log.error(f'Could not remove nodes from the graph: {node_ids}')

        # make sure that graph has the expected number of edges and nodes after routing
        if self.graph.ecount() != self.ecount:
            self.log.error(
                f'Graph has incorrect number of edges: {self.graph.ecount()} is not {self.ecount}'
            )
        if self.graph.vcount() != self.vcount:
            self.log.error(
                f'Graph has incorrect number of nodes: {self.graph.vcount()} is not {self.vcount}'
            )
