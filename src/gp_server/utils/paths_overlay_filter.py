"""
This module provides functionality for filtering out paths with nearly identical geometries. 
"""

from typing import List, Union
from gp_server.app.path import Path
from gp_server.app.logger import Logger


def __get_path_overlay_candidates_by_len(
    param_path: Path, 
    all_paths: List[Path], 
    len_diff: int = 25
) -> List[Path]:
    """Returns paths with length difference not greater or less than specified in [len_diff] (m)
    compared to the length of [path]. If [all_paths] contains [param_path], the latter is included in the returned list.
    """
    return [
        path for path in all_paths 
        if (path.length < (param_path.length + len_diff)) & (path.length > (param_path.length - len_diff))
    ]


def __get_overlapping_paths(
    log: Logger, 
    param_path: Path, 
    compare_paths: List[Path], 
    buffer_m: int = None
) -> List[Path]:
    """Returns [compare_paths] that are within a buffered geometry of [param_path].
    """
    overlapping_paths = [param_path]
    path_geom_buff = param_path.geometry.buffer(buffer_m)
    for compare_path in [compare_path for compare_path in compare_paths if compare_path.name != param_path.name]:
        bool_within = compare_path.geometry.within(path_geom_buff)
        if bool_within:
            overlapping_paths.append(compare_path)
    if len(overlapping_paths) > 1: 
        log.debug(f'Found {len(overlapping_paths)} overlapping paths for: {param_path.name} - {[path.name for path in overlapping_paths]}')
    return overlapping_paths


def __get_least_cost_path(
    paths: List[Path], 
    cost_attr: str = 'nei_norm'
) -> Path:
    """Returns the least expensive (best) path by given cost attribute.
    """
    if len(paths) == 1:
        return next(iter(paths))
    ordered = paths.copy()
    def get_cost(path: Path):
        if cost_attr == 'nei_norm':
            return path.noise_attrs.nei_norm
        if cost_attr == 'aqc_norm':
            return path.aqi_attrs.aqc_norm
    ordered.sort(key=get_cost)
    return ordered[0]


def get_unique_paths_by_geom_overlay(
    log: Logger, 
    all_paths: List[Path], 
    buffer_m: int = None, 
    cost_attr: str = 'nei_norm'
) -> Union[List[str], None]:
    """Filters a list of paths by comparing buffered line geometries of the paths and selecting only the unique paths by given buffer_m (m).

    Args:
        all_paths: Both fastest and exposure optimized paths.
        buffer_m: A buffer size in meters with which the path geometries will be buffered when comparing path geometries.
        cost_attr: The name of a cost attribute to minimize when selecting the best of overlapping paths.
    Note:
        Filters out fastest path if an overlapping green path is found to replace it.
    Returns:
        A filtered list of paths having nearly unique line geometry with respect to the given buffer_m.
        None if PathSet contains only one path.
    """
    if len(all_paths) == 1:
        return None
    paths_already_overlapped = []
    filtered_paths_names = []
    for path in all_paths:
        if path.name not in filtered_paths_names and path.name not in paths_already_overlapped:
            overlay_candidates = __get_path_overlay_candidates_by_len(path, all_paths, len_diff=25)
            overlapping_paths = __get_overlapping_paths(log, path, overlay_candidates, buffer_m)
            best_overlapping_path = __get_least_cost_path(overlapping_paths, cost_attr=cost_attr)
            if best_overlapping_path.name not in filtered_paths_names:
                filtered_paths_names.append(best_overlapping_path.name)
            paths_already_overlapped += [path.name for path in overlapping_paths]

    log.debug(f'Filtered {len(filtered_paths_names)} unique paths from {len(all_paths)} unique paths by overlay')
    return filtered_paths_names
