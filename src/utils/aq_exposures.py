"""
This module provides various functions for assessing and calculating expsoures to air pollution. 
The functions are needed in calculating AQI based costs for green path route optimization and in comparing 
exposures to air pollution between paths.

"""

from typing import List, Set, Dict, Tuple

def get_aq_sensitivities(subset: bool = False) -> List[float]:
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
    if (subset == True):
        return [ 0.2, 0.5, 1, 3, 6, 10, 20 ]
    else:
        return [ 0.2, 0.5, 1, 3, 6, 10, 20, 35 ]

def get_aqi_coeff(aqi: float) -> float:
    """Returns cost coefficient for calculating AQI based costs.
    """
    return (aqi - 1) / 4

def get_aqi_cost(length: float, aqi_coeff: float = None, aqi: float = None, sen: float = 1.0) -> float:
    """Returns AQI based cost based on exposure (distance) to certain AQI. Either aqi or aqi_coeff must be
    given as parameter. If sensitivity value is specified, the cost is multiplied by it.
    """
    if aqi_coeff is not None:
        return round(length * aqi_coeff, 2) * sen
    elif aqi is not None:
        return round(length * get_aqi_coeff(aqi), 2) * sen
    else:
        raise ValueError('Either aqi_coeff or aqi argument must be defined')

def get_aqi_costs(aqi_exp: Tuple[float, float], sens: List[float]) -> Dict[str, float]:
    """Returns a set of AQI based costs as dictionary. The set is based on a set of different sensitivities (sens).
    
    Args:
        aqi_exp: A tuple containing an AQI value and distance (exposure) in meters. 
    """
    aqi_coeff = get_aqi_coeff(aqi_exp[0])
    aq_costs = { 'aqc_'+ str(sen) : get_aqi_cost(aqi_exp[1], aqi_coeff=aqi_coeff, sen=sen) for sen in sens }
    return aq_costs
