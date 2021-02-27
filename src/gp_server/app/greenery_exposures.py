from typing import Dict, List, Tuple
from math import ceil
from collections import defaultdict
import gp_server.env as env


def get_gvi_sensitivities() -> List[float]:

    if env.gvi_sensitivities:
        return env.gvi_sensitivities
    
    return [2, 4, 8]


def get_gvi_adjusted_cost(
    length: float,
    gvi: float,
    length_b: float = None,
    sen: float = 1.0
) -> float:
    """Calculates GVI adjusted edge cost for GVI optimized routing.
    To find high GVI paths, we have to assign lower costs for edges with high GVI and
    higher costs for edges with low GVI. Negative costs cannot be used (with Dijkstra's),
    so a temporarily inverted concept (of GVI) "greyness index" is needed. 
    Higher sensitivity coefficient will give paths of higher GVI (i.e. lower "greyness"). 

    Args:
        length (float): Length of the edge.
        gvi (float): GVI of the edge (0-1).
        length_b (float): Biking cost ("adjusted length") of the edge (optional, for biking).
        sen (float): Sensitivity coefficient (optional, default = 1)

    The function employs the following four assumptions: 
        1) "greyness index" = 1 - gvi
        2) "greyness cost" = (1 - gvi) * length
        3) base cost = either length or length_b (if the latter is given)
        4) GVI adjusted cost = base cost (length) + greyness cost * sensitivity
    """

    base_cost = length_b if length_b else length
    
    return round(base_cost + (1 - gvi) * length * sen, 2)
    

def get_mean_gvi(gvi_exps: List[Tuple[float, float]]) -> float:
    """Returns mean GVI by the list of GVI + length pairs (tuples).
    """
    length = sum([length for _, length in gvi_exps])
    sum_gvi = sum([gvi * length for gvi, length in gvi_exps])
    return round(sum_gvi/length, 2)


def get_gvi_class(gvi: float) -> int:
    """Classifies GVI index to one of nine classes from 1 to 10.
    The returned number represents the upper boundary of an 0.1 wide GVI interval to which
    the GVI value belongs. For example, the GVI class (number) 8 is returned for GVI value 0.73.
    """
    if not isinstance(gvi, float) or gvi > 1 or gvi < 0:
        raise ValueError(f'GVI value is invalid: {gvi}')
    
    return ceil(gvi * 10)


def aggregate_gvi_class_exps(gvi_exps: List[Tuple[float, float]]) -> Dict[int, float]:
    """Aggregates GVI exposures to nine 0.1 wide GVI ranges and returns a new dictionary
    where the keys are the names of the GVI classes.
    """
    gvi_class_exps = defaultdict(float)
    
    for gvi, exp in gvi_exps:
        gvi_class_exps[get_gvi_class(gvi)] += exp
    
    return { 
        gvi_class: round(exp, 3) 
        for gvi_class, exp 
        in gvi_class_exps.items()
    }


def get_gvi_class_pcts(gvi_class_exps: Dict[int, float]) -> Dict[int, float]:
    
    length = sum(gvi_class_exps.values())

    return { 
        gvi_class: round(exp * 100 / length, 3)
        for gvi_class, exp 
        in gvi_class_exps.items() 
    }
