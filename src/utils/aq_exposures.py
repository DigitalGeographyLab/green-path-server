"""
This module provides various functions for assessing and calculating expsoures to air pollution. 
The functions are needed in calculating AQI based costs for green path route optimization and in comparing 
exposures to air pollution between paths.

"""

from collections import defaultdict
from app.constants import RoutingMode, TravelMode, cost_prefix_dict
from typing import List, Dict, Tuple
from math import floor
import numpy as np


class InvalidAqiException(Exception):
    pass


def get_aq_sensitivities() -> List[float]:
    """Returns a set of AQ sensitivity coefficients that can be used in calculating AQI based costs to edges and
    subsequently optimizing green paths that minimize the total exposure to air pollution.

    Args:
        subset: A boolean variable indicating whether a subset of sensitivities should be returned.
    Note:
        The subset should only contain values that are present in the full set as the full set is used to assign the
        cost attributes to the graph.
    Returns:
        A list of AQ sensitivity coefficients.
    """
    return [ 5, 15, 30 ]


def get_aqi_coeff(aqi: float) -> float:
    """Returns cost coefficient for calculating AQI based costs. Raises InvalidAqiException if AQI is either missing
    (aqi = 0.0) or invalid (aqi < 0.95). 
    """
    if (aqi < 0.95):
        raise InvalidAqiException('Received invalid AQI value: '+ str(aqi))
    elif (aqi < 1.0):
        return 0
    else:
        return (aqi - 1) / 4


def calc_aqi_cost(
    length: float, 
    aqi_coeff: float, 
    length_b: float = None, 
    sen: float = 1.0
) -> float:
    """Returns AQI based cost based on exposure (distance) to certain AQI. 
    If sensitivity value is specified, the AQI based part of the cost is multiplied by it.
    """
    base_cost = length if not length_b else length_b
    return round(base_cost + length * aqi_coeff * sen, 2)


def get_aqi_costs(
    aqi: float, 
    length: float, 
    sens: List[float], 
    length_b: float = None, 
    travel_mode: TravelMode = TravelMode.WALK
) -> Dict[str, float]:
    """Returns a set of AQI based costs as dictionary. The set is based on a set of different sensitivities (sens).
    If AQI value is missing of invalid, high AQI costs are returned in order to avoid using the edge in AQI based routing.
    Additionally, returned dictionary contains attribute has_aqi, indicating whether AQI costs are valid (based on valid AQI).
    
    Args:
        aqi_exp: A tuple containing an AQI value and distance (exposure) in meters (aqi: float, distance: float).
        length: A length value to use as a base cost.
    """
    try:
        aqi_coeff = get_aqi_coeff(aqi)
    except InvalidAqiException:
        # assign high aq costs to edges without aqi data
        aqi_coeff = 10

    cost_prefix = cost_prefix_dict[travel_mode][RoutingMode.CLEAN]
    aq_costs = { cost_prefix + str(sen) : calc_aqi_cost(length, aqi_coeff, length_b=length_b, sen=sen) for sen in sens }
    return aq_costs


def get_aqi_cost_from_exp(
    aqi_exp: Tuple[float, float], 
    sen: float = 1.0
) -> float:
    """Returns an AQI cost for a single AQI exposure (aqi, exposure as meters). 
    Length is not included in the cost as base cost.
    """
    return round(aqi_exp[1] * get_aqi_coeff(aqi_exp[0]) * sen, 2)


def get_total_aqi_cost_from_exps(
    aqi_exp_list: List[Tuple[float, float]], 
    sen: float = 1
) -> float:
    """Returns the total AQI cost from a list of AQI exposures (with sensitivity of 1.0). 
    Length is not included in the costs as base cost.
    """
    costs = [get_aqi_cost_from_exp(aqi_exp, sen) for aqi_exp in aqi_exp_list]
    return sum(costs)


def get_aqi_class(aqi: float) -> int:
    """Returns AQI class identifier, that is in the range from 2 to 10. Returns 0 if the given AQI is invalid.
    AQI classes represent (9 x) 0.5 intervals in the original AQI scale from 1.0 to 5.0.
    """
    return floor(aqi * 2) if np.isfinite(aqi) else 0


def aggregate_aqi_class_exps(aqi_exp_list: List[Tuple[float, float]]) -> Dict[int, float]:
    """Returns a dictionary of aggregated exposures to different AQI classes (e.g. { 1: 305, 2: 205, 3: 50.4 } )

    Args:
        aqi_exp_list: A list of AQI exposures (e.g. [ (1.5, 42.4), (1.1, 13.4), (1.7, 52.3) ])
    """
    aqi_cl_exps = defaultdict(float)
    
    for aqi, length in aqi_exp_list:
        aqi_cl_exps[get_aqi_class(aqi)] += length
    
    # round aqi class exposures
    return { 
        aqi_class: round(length, 3) 
        for aqi_class, length 
        in aqi_cl_exps.items()
    }


def get_aqi_class_pcts(aqi_cl_exps: Dict[int, float], length: float) -> dict:
    """Returns the percentages of exposures to different AQI classes as a dictionary (e.g. { 1: 75.0, 2: 25.0 } ).
    
    Args:
        aqi_cl_exps: A dictionary of exposures to different AQI classes (1, 2, 3...) as distances (m).
        length: The length of the path.
    """

    return {
        aqi_class: round(aqi_class_length * 100 / length, 3)
        for aqi_class, aqi_class_length 
        in aqi_cl_exps.items()
    }


def get_mean_aqi(aqi_exp_list: List[Tuple[float, float]]) -> float:
    """Calculates and returns the mean aqi from a list of aqi exposures (list of tuples: (aqi, distance)).
    """
    total_dist = sum([aqi_exp[1] for aqi_exp in aqi_exp_list])
    total_aqi = sum([aqi_exp[0] * aqi_exp[1] for aqi_exp in aqi_exp_list])
    return round(total_aqi/total_dist, 2)
