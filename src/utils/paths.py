"""
This module provides functions for aggregating paths based on their geometries. 

Todo:
    * Add support for using other edge weights than noise (e.g. AQI)

"""

from typing import List, Set, Dict, Tuple, Optional

def get_similar_length_paths(paths: List[dict], path: dict, len_diff: int = 25) -> List[dict]:
    """Returns paths with length difference not greater or less than specified in [len_diff] (m)
    compared to the length of [path].
    """
    path_len = path['properties']['length']
    similar_len_paths = [path for path in paths if (path['properties']['length'] < (path_len + len_diff)) & (path['properties']['length'] > (path_len - len_diff))]
    return similar_len_paths

def get_overlapping_paths(compare_paths: List[dict], path: dict, tolerance: int = None) -> List[dict]:
    """Returns overlapping paths by comparing buffered geometries of [paths] to buffered geometry of [path].
    """
    overlapping = [path]
    path_geom = path['properties']['geometry']
    path_geom_buff = path_geom.buffer(tolerance)
    for compare_path in [compare_path for compare_path in compare_paths if path['properties']['id'] != compare_path['properties']['id']]:
        comp_path_geom = compare_path['properties']['geometry']
        if (comp_path_geom.within(path_geom_buff)):
            # print('found overlap:', path['properties']['id'], compare_path['properties']['id'])
            overlapping.append(compare_path)
    return overlapping

def get_best_path(paths: List[dict], cost_attr: str = 'nei_norm') -> dict:
    """Returns the least expensive (best) path by given cost attribute.
    """
    ordered = paths.copy()
    def get_score(path):
        return path['properties'][cost_attr]
    ordered.sort(key=get_score)
    return ordered[0]

def remove_duplicate_geom_paths(paths: List[dict], tolerance: int = None, remove_geom_prop: bool = True, cost_attr: str = 'nei_norm', logging: bool = True) -> List[dict]:
    """Filters a list of paths by comparing buffered line geometries of the paths and selecting only the unique paths by given tolerance (m).

    Args:
        paths: A list of paths to filter.
        tolerance: A tolerance in meters with which the path geometries will be buffered when comparing path geometries.
        remove_geom_prop: A boolean value indicating whether the geometry property of the paths should be removed or retained.
        cost_attr: The name of a cost attribute to minimize when selecting the best of overlapping paths.
    Note:
        If the length of the shortest quiet path is no longer than 10 m more than the length of the shortest path,
        the shortest quiet path is set as the shortest path and shortest path is removed from the list of paths.
    Returns:
        A filtered list of paths having unique line geometry with respect to given tolerance.
    """
    all_overlapping_paths = []
    filtered_paths_ids = []
    filtered_paths = []
    shortest_path = [path for path in paths if path['properties']['type'] == 'short'][0]
    quiet_paths = [path for path in paths if path['properties']['type'] == 'quiet']
    for path in quiet_paths:
        if (path['properties']['type'] != 'short'):
            path_id = path['properties']['id']
            if (path_id in filtered_paths_ids or path_id in all_overlapping_paths):
                continue
            similar_len_paths = get_similar_length_paths(paths, path)
            overlapping_paths = get_overlapping_paths(similar_len_paths, path, tolerance)
            if (len(overlapping_paths) > 1):
                best_overlapping_path = get_best_path(overlapping_paths, cost_attr=cost_attr)
                best_overlapping_id = best_overlapping_path['properties']['id']
                if (best_overlapping_id not in filtered_paths_ids):
                    filtered_paths.append(best_overlapping_path)
                    filtered_paths_ids.append(best_overlapping_id)
                all_overlapping_paths += [path['properties']['id'] for path in overlapping_paths]
            else:
                if (path_id not in filtered_paths_ids):
                    filtered_paths.append(path)
                    filtered_paths_ids.append(path_id)
    # check if shortest path is shorter than shortest quiet path
    shortest_quiet_path = filtered_paths[0]
    if (shortest_quiet_path['properties']['length'] - shortest_path['properties']['length'] > 10):
        # print('set shortest path as shortest')
        if ('short_p' not in filtered_paths_ids):
            filtered_paths.append(shortest_path)
    else:
        # print('set shortest quiet path as shortest')
        if ('short_p' not in filtered_paths_ids):
            filtered_paths[0]['properties']['type'] = 'short'
            filtered_paths[0]['properties']['id'] = 'short_p'
    # delete shapely geometries from path dicts
    if (remove_geom_prop == True):
        for path in filtered_paths:
            del path['properties']['geometry']
    if logging == True: print('found', len(paths), 'of which returned', len(filtered_paths), 'unique paths.')
    return filtered_paths
