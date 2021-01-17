"""
This module provides various functions for assessing and calculating expsoures to traffic noise. 
The functions are useful in calculating noise costs for quiet path route optimization and in comparing exposures to noise
between paths.

"""

from typing import List, Set, Dict, Tuple, Union
from collections import defaultdict
from shapely.geometry import LineString
from utils.igraph import Edge as E
from app.constants import cost_prefix_dict, TravelMode, RoutingMode


def calc_db_cost_v2(db) -> float:
    """Returns a noise cost for given dB based on a linear scale (dB >= 45 & dB <= 75).
    """
    if (db <= 44): 
        return 0.0
    db_cost = (db-40) / (75-40)
    return round(db_cost, 3)


def calc_db_cost_v3(db) -> float:
    """Returns a noise cost for given dB: every 10 dB increase doubles the cost (dB >= 45 & dB <= 75).
    """
    if (db <= 44): return 0.0
    db_cost = pow(10, (0.3 * db)/10)
    return round(db_cost / 100, 3)


def get_db_costs(version: int = 3) -> Dict[int, float]:
    """Returns a set of dB-specific noise cost coefficients. They can be used in calculating the base (noise) cost for edges. 
    (Alternative noise costs can be calculated by multiplying the base noise cost with different noise sensitivities 
    from get_noise_sensitivities())

    Returns:
        A dictionary of noise cost coefficients where the keys refer to the lower boundaries of the 5 dB ranges 
        (e.g. key 50 refers to 50-55 dB range) and the values are the dB-specific noise cost coefficients.
    """
    dbs = list(range(40, 80))
    if (version == 2):
        return { db: calc_db_cost_v2(db) for db in dbs }
    elif (version == 3):
        return { db: calc_db_cost_v3(db) for db in dbs }
    else:
        raise ValueError('Argument version must be either 2 or 3')


def get_noise_sensitivities() -> List[float]:
    """Returns a set of noise sensitivity coefficients that can be used in adding alternative noise-based costs to edges and
    subsequently calculating alternative quiet paths (using different weights for noise cost in routing).
    """
    return [ 0.1, 0.4, 1.3, 3.5, 6 ]


def get_noise_range(db: float) -> int:
    """Returns the lower limit of one of the six pre-defined dB ranges based on dB.
    """
    if db >= 70.0: return 70
    elif db >= 65.0: return 65
    elif db >= 60.0: return 60
    elif db >= 55.0: return 55
    elif db >= 50.0: return 50
    else: return 40


def get_noise_range_exps(noises: dict, total_length: float) -> Dict[int, float]:
    """Calculates aggregated exposures to different noise level ranges.

    Note:
        Noise levels exceeding 70 dB and noise levels lower than 50 dB will be aggregated (separately).

    Returns:
        A dictionary containing exposures (m) to different noise level ranges.
        (e.g. { 40: 15.2, 50: 62.4, 55: 10.5 })
    """
    # aggregate noise exposures to pre-defined dB-ranges
    db_range_lens = defaultdict(float)
    for db, exp in noises.items():
        dB_range = get_noise_range(db)
        db_range_lens[dB_range] += exp
    
    # round exposures
    for k, v in db_range_lens.items():
        db_range_lens[k] = round(v, 3)

    return db_range_lens


def get_noise_range_pcts(dB_range_exps: dict, length: float) -> Dict[int, float]:
    """Calculates percentages of aggregated exposures to different noise levels of total length.

    Note:
        Noise levels exceeding 70 dB are aggregated and as well as noise levels lower than 50 dB. 
    Returns:
        A dictionary containing noise level values with respective percentages.
        (e.g. { 50: 35.00, 60: 65.00 })
    """
    # calculate ratio (%) of each range's length to total length
    range_pcts = {}
    for dB_range in dB_range_exps.keys():
        range_pcts[dB_range] = round(dB_range_exps[dB_range]*100/length, 3)

    return range_pcts


def aggregate_exposures(exp_list: List[dict]) -> Dict[int, float]:
    """Aggregates noise exposures (contaminated distances) from a list of noise exposures. 
    """
    exps = defaultdict(float)
    for db_exps in exp_list:
        for db, exp in db_exps.items():
            exps[db] += exp
    for k, v in exps.items():
        exps[k] = round(v, 3)
    return exps


def get_total_noises_len(noises: Dict[int, float]) -> float:
    """Returns a total length of exposures to all noise levels.
    """
    if (not noises):
        return 0.0
    else:
        return round(sum(noises.values()), 3)


def get_mean_noise_level(noises: dict, length: float) -> float:
    """Returns a mean noise level based on noise exposures weighted by the contaminated distances to different noise levels.
    """
    # estimate mean dB of 5 dB range to be min dB + 2.5 dB
    sum_db = sum([(db + 2.5) * length for db, length in noises.items()])
    mean_db = sum_db/length
    return round(mean_db, 1)


def get_noise_cost(
    noises: Dict[int, float], 
    db_costs: Dict[int, float], 
    sen: float = 1
) -> float:
    """Returns a total noise cost based on contaminated distances to different noise levels, db_costs and noise sensitivity. 
    """
    if not noises:
        return 0.0
    else:
        noise_cost = sum([db_costs[db] * length * sen for db, length in noises.items()])
        return round(noise_cost, 2)


def get_noise_adjusted_edge_cost(
    sensitivity: float,
    db_costs: Dict[int, float],
    noises: Union[dict, None], 
    length: float,
    biking_length: Union[float, None] = None
):
    """Returns composite edge cost as 'base_cost' + 'noise_cost', i.e.
    length + noise exposure based cost. 
    """

    if noises is None:
        # set high noise costs for edges outside data coverage
        noise_cost = 20 * length
    else:
        noise_cost = get_noise_cost(noises, db_costs, sensitivity)

    base_cost = biking_length if biking_length else length

    return round(base_cost + noise_cost, 2) 


def interpolate_link_noises(
    link_len_ratio: float, 
    link_geom: LineString, 
    edge_geom: LineString, 
    edge_noises: dict
) -> dict:
    """Interpolates noise exposures for a split edge by multiplying each contaminated distance with a proportion
    between the edge length to the length of the original edge.
    """
    link_noises = {}
    link_len_ratio = link_geom.length / edge_geom.length
    for db in edge_noises.keys():
        link_noises[db] = round(edge_noises[db] * link_len_ratio, 3)
    return link_noises


def get_link_edge_noise_cost_estimates(sens, db_costs, edge_dict=None, link_geom=None) -> dict:
    """Estimates noise exposures and noise costs for a split edge based on noise exposures of the original edge
    (from which the edge was split). 
    """
    cost_prefix = cost_prefix_dict[TravelMode.WALK][RoutingMode.QUIET]
    cost_prefix_bike = cost_prefix_dict[TravelMode.BIKE][RoutingMode.QUIET]

    cost_attrs = {}
    # estimate link costs based on link length - edge length -ratio and edge noises
    link_len_ratio = link_geom.length / edge_dict[E.geometry.value].length
    cost_attrs[E.noises.value] = interpolate_link_noises(link_len_ratio, link_geom, edge_dict[E.geometry.value], edge_dict[E.noises.value])
    # calculate noise sensitivity specific noise costs
    for sen in sens:
        noise_cost = get_noise_cost(cost_attrs[E.noises.value], db_costs, sen=sen)
        cost_attrs[cost_prefix + str(sen)] = round(link_geom.length + noise_cost, 3)
        cost_attrs[cost_prefix_bike + str(sen)] = round(link_geom.length + noise_cost, 3) # biking costs
    return cost_attrs


def add_db_40_exp_to_noises(noises: Union[dict, None], length: float) -> Dict[int, float]:
    if noises is None or not length or 40 in noises:
        return noises

    total_db_length = get_total_noises_len(noises) if noises else 0.0
    db_40_len = round(length - total_db_length, 2)
    if db_40_len:
        return { 40: db_40_len, **noises }
    
    return noises
