"""
This module provides function for filtering out paths with nearly identical geometries. 

"""

from typing import List, Set, Dict, Tuple
import time
import utils.utils as utils
from utils.path import Path

def get_path_overlay_candidates_by_len(param_path: Path, all_paths: List[Path], len_diff: int = 25, debug=False) -> List[Path]:
    """Returns paths with length difference not greater or less than specified in [len_diff] (m)
    compared to the length of [path]. If [all_paths] contains [param_path], the latter is included in the returned list.
    """
    overlay_candidates = [path for path in all_paths if (path.length < (param_path.length + len_diff)) & (path.length > (param_path.length - len_diff))]
    if (debug == True): 
        if (len(overlay_candidates) > 1): print('found', len(overlay_candidates), "overlap candidates paths for:", param_path.name)
    return overlay_candidates

def get_overlapping_paths(param_path: Path, compare_paths: List[Path], buffer_m: int = None, debug: bool = False) -> List[Path]:
    """Returns [compare_paths] that are within a buffered geometry of [param_path].
    """
    overlapping_paths = [param_path]
    path_geom_buff = param_path.geometry.buffer(buffer_m)
    for compare_path in [compare_path for compare_path in compare_paths if compare_path.name != param_path.name]:
        bool_within = compare_path.geometry.within(path_geom_buff)
        if (bool_within == True):
            overlapping_paths.append(compare_path)
        # if (debug == True): print('Comparison if', compare_path.name, 'is within buffer around:', param_path.name, bool_within)
    if (debug == True): 
        if (len(overlapping_paths) > 1): print('found', len(overlapping_paths), "overlapping paths for:", param_path.name, '-', [path.name for path in overlapping_paths])
    return overlapping_paths

def get_least_cost_path(paths: List[Path], cost_attr: str = 'nei_norm', debug=False) -> Path:
    """Returns the least expensive (best) path by given cost attribute.
    """
    if (len(paths) == 1):
        return next(iter(paths))
    ordered = paths.copy()
    def get_cost(path):
        if (cost_attr == 'nei_norm'):
            return path.noise_attrs.nei_norm
    ordered.sort(key=get_cost)
    if (debug == True): print('got least cost path', ordered[0].name, 'with cost:', get_cost(ordered[0]), cost_attr, 'from:', [get_cost(path) for path in ordered])
    return ordered[0]

def get_unique_paths_by_geom_overlay(all_paths: List[Path], buffer_m: int = None, cost_attr: str = 'nei_norm', debug: bool = True) -> List[str]:
    """Filters a list of paths by comparing buffered line geometries of the paths and selecting only the unique paths by given buffer_m (m).

    Args:
        all_paths: Both short and green paths.
        buffer_m: A buffer size in meters with which the path geometries will be buffered when comparing path geometries.
        cost_attr: The name of a cost attribute to minimize when selecting the best of overlapping paths.
    Note:
        Filters out shortest path if an overlapping green path is found to replace it.
    Returns:
        A filtered list of paths having nearly unique line geometry with respect to the given buffer_m.
        None if PathSet contains only one path.
    """
    if (len(all_paths) == 1):
        return None
    start_time = time.time()
    paths_already_overlapped = []
    filtered_paths_names = []
    for path in all_paths:
        if (path.name not in filtered_paths_names and path.name not in paths_already_overlapped):
            overlay_candidates = get_path_overlay_candidates_by_len(path, all_paths, len_diff=25, debug=debug)
            overlapping_paths = get_overlapping_paths(path, overlay_candidates, buffer_m, debug=debug)
            best_overlapping_path = get_least_cost_path(overlapping_paths, cost_attr=cost_attr, debug=debug)
            if (best_overlapping_path.name not in filtered_paths_names):
                filtered_paths_names.append(best_overlapping_path.name)
            paths_already_overlapped += [path.name for path in overlapping_paths]

    if (debug == True): print('filtered', len(filtered_paths_names), 'unique paths from', len(all_paths), 'unique paths by overlay')
    if (debug == True): utils.print_duration(start_time, 'path overlay filtering done')
    return filtered_paths_names
