from typing import Dict, List, Tuple
from math import ceil
from collections import defaultdict


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
        gvi_class: round(exp, 2) 
        for gvi_class, exp 
        in gvi_class_exps.items()
    }


def get_gvi_class_pcts(gvi_class_exps: Dict[int, float]) -> Dict[int, float]:
    
    length = sum(gvi_class_exps.values())

    return { 
        gvi_class: round(exp * 100 / length, 2) 
        for gvi_class, exp 
        in gvi_class_exps.items() 
    }
