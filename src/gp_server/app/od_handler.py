import common.geometry as geom_utils
from gp_server.app.types import LinkToEdgeSpec, NearestEdge, OdNodeData, OdData
from typing import Dict, Tuple, Union
from shapely.geometry import Point, LineString
from gp_server.app.graph_handler import GraphHandler
from common.igraph import Edge as E
from gp_server.app.constants import RoutingException, ErrorKey


def __get_closest_point_on_line(line: LineString, point: Point) -> Point:
    """Finds the closest point (Point) on a line to given point and returns it.
    """
    projected = line.project(point)
    closest_point = line.interpolate(projected)
    return closest_point


def __calculate_link_noises(
    noises: Union[Dict[int, float], None],
    link_len_ratio: float
) -> Union[Dict[int, float], None]:
    if noises:
        return {
            attr: round(value * link_len_ratio, 3)
            for attr, value in noises.items()
        }
    return noises


def __project_link_edge_attrs(
    from_node: int,
    to_node: int,
    link_geom: LineString,
    link_geom_wgs,
    on_edge_attrs: dict
) -> dict:
    """Creates edge attribute dictionary for a linking edge based on a base edge and ratio of
    the lengths of the two.
    """
    link_len = link_geom.length
    link_len_ratio = link_len / on_edge_attrs[E.length.value]

    base_attrs = {
        E.uv.value: (from_node, to_node),
        E.length.value: round(link_len, 2),
        E.geometry.value: link_geom,
        E.geom_wgs.value: link_geom_wgs,
        E.allows_biking.value: on_edge_attrs[E.allows_biking.value],
        E.gvi.value: on_edge_attrs.get(E.gvi.value, None),
        E.noises.value: __calculate_link_noises(
            on_edge_attrs.get(E.noises.value, None),
            link_len_ratio
        ),
        E.aqi.value: on_edge_attrs.get(E.aqi.value, None)
    }
    cost_attrs = {
        attr: round(value * link_len_ratio, 2)
        for attr, value in on_edge_attrs.items()
        if attr.startswith('c_')  # prefix of all cost attributes
    }

    return {**base_attrs, **cost_attrs}


def get_link_edge_data(
    new_node_id: int,
    link_to_edge_spec: LinkToEdgeSpec,
    create_inbound_links: bool,
    create_outbound_links: bool
) -> Tuple[dict]:
    """
    Returns complete edge attribute dictionaries for new linking edges.

    Args:
        new_node_id: An identifier of the new node.
        split_point: A point geometry of the new node (on an existing edge).
        edge: All attributes of the edge on which the new node was created.
        create_inbound_links: A boolean variable indicating whether links should be inbound.
        create_outbound_links: A boolean variable indicating whether links should be outbound.
    """
    e_node_from = link_to_edge_spec.edge[E.uv.value][0]
    e_node_to = link_to_edge_spec.edge[E.uv.value][1]

    # create geometry objects for the links
    link1, link2 = geom_utils.split_line_at_point(
        link_to_edge_spec.edge[E.geometry.value],
        link_to_edge_spec.snap_point
    )
    link1_wgs, link2_wgs = tuple(
        geom_utils.project_geom(link, geom_epsg=3879, to_epsg=4326) for link in (link1, link2)
    )
    link1_rev, link1_wgs_rev, link2_rev, link2_wgs_rev = (
        LineString(link.coords[::-1]) for link in (link1, link1_wgs, link2, link2_wgs)
    )

    outbound_links = tuple(
        __project_link_edge_attrs(u, v, geom, geom_wgs, link_to_edge_spec.edge)
        for u, v, geom, geom_wgs in (
            (new_node_id, e_node_from, link1_rev, link1_wgs_rev),
            (new_node_id, e_node_to, link2, link2_wgs),
        )
    ) if create_outbound_links else ()

    inbound_links = tuple(
        __project_link_edge_attrs(u, v, geom, geom_wgs, link_to_edge_spec.edge)
        for u, v, geom, geom_wgs in (
            (e_node_from, new_node_id, link1, link1_wgs),
            (e_node_to, new_node_id, link2_rev, link2_wgs_rev)
        )
    ) if create_inbound_links else ()

    return outbound_links + inbound_links


def __maybe_use_nearest_existing_node(
    avoid_node_creation: bool,
    long_distance: bool,
    nearest_node: int,
    nearest_node_dist: float,
    nearest_edge: NearestEdge
) -> Union[OdNodeData, None]:

    nearest_node_vs_edge_dist = nearest_node_dist - nearest_edge.distance
    # use the nearest node if it is on the nearest edge and at least almost
    # as near as the nearest edge, this can give a significant performance boost
    # as adding (or deleting) linking edges to the graph is expensive
    if avoid_node_creation:
        acceptable_od_offset = 30 if not long_distance else 40
        if (nearest_node_vs_edge_dist < acceptable_od_offset and
                (nearest_node in nearest_edge.attrs[E.uv.value])):
            return OdNodeData(
                id=nearest_node,
                is_temp_node=False
            )
    # snap 10 m to nearest node regardless of avoid_node_creation
    if nearest_node_vs_edge_dist < 10:
        return OdNodeData(
            id=nearest_node,
            is_temp_node=False
        )

    return None


def __select_nearest_edge(
    nearest_edge_point: Point,
    nearest_edge: NearestEdge,
    temp_link_edges: Tuple[dict],
) -> Union[NearestEdge]:
    """Returns temp (i.e. link) edge as nearest edge for O/D creation if is as near to the Point
    as the nearest normal edge.
    """

    # check if the nearest edge of the destination is one of the linking edges created for origin
    for link_edge in temp_link_edges:
        link_edge_dist = nearest_edge_point.distance(link_edge[E.geometry.value])
        if link_edge_dist < 0.1:
            return NearestEdge(
                link_edge,
                link_edge_dist
            )

    return nearest_edge


def get_nearest_node(
    G: GraphHandler,
    point: Point,
    avoid_node_creation: bool,
    temp_link_edges: Tuple[dict] = (),
    long_distance: bool = False
) -> OdNodeData:

    nearest_edge = G.find_nearest_edge(point)
    if not nearest_edge:
        raise Exception('Nearest edge not found')

    nearest_node: int = G.find_nearest_node(point)
    if not nearest_node:
        raise Exception('Nearest node not found')

    nearest_node_geom = G.get_node_point_geom(nearest_node)
    nearest_edge_point = __get_closest_point_on_line(nearest_edge.attrs[E.geometry.value], point)
    nearest_node_dist = nearest_node_geom.distance(point)

    od_as_nearest_node = __maybe_use_nearest_existing_node(
        avoid_node_creation,
        long_distance,
        nearest_node,
        nearest_node_dist,
        nearest_edge
    )
    if od_as_nearest_node:
        return od_as_nearest_node

    # still here, thus creating a new node to graph and linking edges for it

    nearest_edge = __select_nearest_edge(
        nearest_edge_point,
        nearest_edge,
        temp_link_edges
    )

    # create a new node on the nearest edge to the graph
    new_node = G.add_new_node_to_graph(nearest_edge_point)
    # new edges from the new node to existing nodes need to be created to the graph
    # hence return the geometry of the nearest edge and the nearest point on the nearest edge
    return OdNodeData(
        id=new_node,
        is_temp_node=True,
        link_to_edge_spec=LinkToEdgeSpec(
            edge=nearest_edge.attrs,
            snap_point=nearest_edge_point
        )
    )


def get_orig_dest_nodes_and_linking_edges(
    G: GraphHandler,
    orig_point: Point,
    dest_point: Point
) -> OdData:
    """Selects nearest nodes ad OD if they are "near enough", otherwise creates new nodes
    either on the nearest existing edges or on the previously created links (i.e. temporary) edges.
    """
    orig_link_edges = ()
    dest_link_edges = ()
    long_distance: bool = orig_point.distance(dest_point) > 5000

    try:
        orig_node = get_nearest_node(
            G,
            orig_point,
            avoid_node_creation=True,
            long_distance=long_distance
        )
    except Exception:
        raise RoutingException(ErrorKey.ORIGIN_NOT_FOUND.value)

    # add linking edges to graph if new node was created (on the nearest edge)
    if orig_node.link_to_edge_spec:
        orig_link_edges = get_link_edge_data(
            orig_node.id,
            orig_node.link_to_edge_spec,
            create_inbound_links=False,
            create_outbound_links=True
        )

    try:
        dest_node = get_nearest_node(
            G,
            dest_point,
            avoid_node_creation=not orig_link_edges,
            temp_link_edges=orig_link_edges,
            long_distance=long_distance
        )
    except Exception:
        raise RoutingException(ErrorKey.DESTINATION_NOT_FOUND.value)

    # add linking edges to graph if new node was created (on the nearest edge)
    if dest_node.link_to_edge_spec:
        dest_link_edges = get_link_edge_data(
            dest_node.id,
            dest_node.link_to_edge_spec,
            create_inbound_links=True,
            create_outbound_links=False,
        )

    G.add_new_edges_to_graph(orig_link_edges + dest_link_edges)

    return OdData(orig_node, dest_node, orig_link_edges, dest_link_edges)
