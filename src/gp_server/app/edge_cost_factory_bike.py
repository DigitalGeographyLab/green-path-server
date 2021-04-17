from gp_server.conf import walk_speed_ms, bike_speed_ms
from common.igraph import Edge as E
from igraph import Graph
from typing import Union
from collections import Counter
from gp_server.app.types import Bikeability


def get_bikeability(
    allows_biking: bool,
    is_stairs: bool
) -> Bikeability:
    if not allows_biking and is_stairs:
        return Bikeability.NO_BIKE_STAIRS

    if not allows_biking and not is_stairs:
        return Bikeability.NO_BIKE

    if allows_biking and is_stairs:
        return Bikeability.BIKE_OK_STAIRS

    if allows_biking:
        return Bikeability.BIKE_OK

    raise ValueError(f'Could not set bikeability from: {allows_biking} & {is_stairs}')


def get_bike_cost(
    length: Union[float, None],
    bikeability: Bikeability,
    safety_factor: Union[float, None],
    bike_walk_time_ratio: float
) -> float:
    """
    Returns biking cost that is proportional to travel time and adjusted with
    biking safety factor (if provided).
    """
    if not length:
        return 0

    # normal stairs (i.e. NO_BIKE_STAIRS)
    if bikeability == Bikeability.NO_BIKE_STAIRS:
        return length * bike_walk_time_ratio * 15

    # no bike or bikeable stairs (i.e. BIKE_OK_STAIRS) = walking speed?
    if bikeability == Bikeability.NO_BIKE or bikeability == Bikeability.BIKE_OK_STAIRS:
        return length * bike_walk_time_ratio * 1.2  # add 20 % extra cost for walking with bike

    if safety_factor:
        return length * safety_factor

    return length


def get_bikeabilities(graph: Graph):
    return [
        get_bikeability(allows_biking, is_stairs)
        for allows_biking, is_stairs
        in zip(
            graph.es[E.allows_biking.value],
            graph.es[E.is_stairs.value]
        )
    ]


def set_biking_costs(graph, log):
    bike_walk_time_ratio = bike_speed_ms / walk_speed_ms

    log.info(
        f'Using walk speed: {walk_speed_ms}, bike speed: {bike_speed_ms}'
        f' and bike_walk_time_ratio: {round(bike_walk_time_ratio, 2)}'
    )

    bikeabilities = get_bikeabilities(graph)
    log.info(f'Bikeability counts: {dict(Counter(bikeabilities))}')

    # biking time costs
    graph.es[E.bike_time_cost.value] = [
        round(
            get_bike_cost(
                length,
                bikeability,
                None,
                bike_walk_time_ratio
            ), 1
        )
        for length, bikeability
        in zip(
            graph.es[E.length.value],
            bikeabilities
        )
    ]

    # biking safety costs
    graph.es[E.bike_safety_cost.value] = [
        round(
            get_bike_cost(
                length,
                bikeability,
                safety,
                bike_walk_time_ratio
            ), 1
        )
        for length, bikeability, safety
        in zip(
            graph.es[E.length.value],
            bikeabilities,
            graph.es[E.bike_safety_factor.value]
        )
    ]
