from gp_server.app.types import RoutingConf
from igraph import Graph
from shapely.geometry import LineString
from gp_server.app.constants import cost_prefix_dict, TravelMode, RoutingMode
from common.igraph import Edge as E
import gp_server.app.noise_exposures as noise_exps
import gp_server.app.greenery_exposures as gvi_exps
from gp_server.conf import conf
import gp_server.app.edge_cost_factory_bike as bike_costs


def set_biking_costs(graph: Graph, log):
    bike_costs.set_biking_costs(graph, log)
    # remove now redundant edge attributes
    del graph.es[E.bike_safety_factor.value]
    del graph.es[E.is_stairs.value]


def set_noise_costs_to_edges(graph: Graph, routing_conf: RoutingConf):
    """Updates all noise cost attributes to a graph.
    """
    cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.QUIET]
    cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.QUIET]

    noises_list = graph.es[E.noises.value]
    length_list = graph.es[E.length.value]
    has_geom_list = [isinstance(geom, LineString) for geom in list(graph.es[E.geometry.value])]

    # update dB 40 lengths to graph (the lowest level in noise data is 45)
    graph.es[E.noises.value] = [
        noise_exps.add_db_40_exp_to_noises(noises, length)
        for noises, length
        in zip(noises_list, length_list)
    ]

    # get noises list again after adding 40 dB lengths
    noises_list = graph.es[E.noises.value]

    for sen in routing_conf.noise_sensitivities:

        if conf.walking_enabled:
            cost_attr = cost_prefix + str(sen)
            graph.es[cost_attr] = [
                noise_exps.get_noise_adjusted_edge_cost(
                    sen, routing_conf.db_costs, noises, length
                ) if has_geom else 0.0
                for length, noises, has_geom
                in zip(length_list, noises_list, has_geom_list)
            ]

        if conf.cycling_enabled:
            bike_time_costs = graph.es[E.bike_time_cost.value]
            cost_attr = cost_prefix_bike + str(sen)
            graph.es[cost_attr] = [
                noise_exps.get_noise_adjusted_edge_cost(
                    sen, routing_conf.db_costs, noises, length, bike_time_cost
                ) if has_geom else 0.0
                for length, bike_time_cost, noises, has_geom
                in zip(
                    length_list, bike_time_costs, noises_list, has_geom_list
                )
            ]


def set_gvi_costs_to_graph(graph: Graph, routing_conf: RoutingConf):
    """Updates all greenery cost attributes to a graph.
    """
    cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.GREEN]
    cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.GREEN]

    lengths = graph.es[E.length.value]
    gvi_list = graph.es[E.gvi.value]
    has_geom_list = [isinstance(geom, LineString) for geom in list(graph.es[E.geometry.value])]

    for sen in routing_conf.gvi_sensitivities:

        if conf.walking_enabled:
            cost_attr = cost_prefix + str(sen)
            graph.es[cost_attr] = [
                gvi_exps.get_gvi_adjusted_cost(length, gvi, sensitivity=sen)
                if has_geom else 0.0
                for length, gvi, has_geom
                in zip(lengths, gvi_list, has_geom_list)
            ]

        if conf.cycling_enabled:
            bike_time_costs = graph.es[E.bike_time_cost.value]
            cost_attr = cost_prefix_bike + str(sen)
            graph.es[cost_attr] = [
                gvi_exps.get_gvi_adjusted_cost(
                    length, gvi, bike_time_cost=bike_time_cost, sensitivity=sen
                )
                if has_geom else 0.0
                for length, bike_time_cost, gvi, has_geom
                in zip(
                    lengths, bike_time_costs, gvi_list, has_geom_list
                )
            ]
