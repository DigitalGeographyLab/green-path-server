"""
This module provides constants and functions needed in quiet path optimization. 

"""

from typing import List, Set, Dict, Tuple
import geopandas as gpd
import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps

def get_db_costs() -> Dict[int, float]:
    """Returns a set of dB-specific noise cost coefficients. They can be used in calculating the base noise cost for edges. 
    (Alternative noise costs can be calculated by multiplying the base noise cost with different noise tolerances 
    from get_noise_tolerances())

    Returns:
        A dictionary of noise cost coefficients where the keys are the lower boundaries of the 5 dB ranges 
        (e.g. key 50 refers to 50-55 dB range) and the values are the dB-specific noise cost coefficients.
    """
    return { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }

def get_noise_tolerances() -> List[float]:
    """Returns a set of noise tolerance coefficients that can be used in adding alternative noise-based costs to edges and
    subsequently calculating alternative quiet paths (using different weights for noise cost in routing).
    
    Returns:
        A list of noise tolerance values.
    """
    return [ 0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40 ]

def get_short_quiet_paths_comparison_for_dicts(paths: List[dict]) -> List[dict]:
    """Finds the shortest path from a list of paths and compares exposures to noise (and path length) between the 
    quiet paths and the shortest path (mean dB etc.). The differences are added as attributes to the paths' 'properties' -dictionaries.

    Args:
        paths: A list of paths as dictionaries. 
    Returns:
        A similar list of dictionaries (paths) as given but with the added properties.
    """
    comp_paths = paths.copy()
    path_s = [path for path in comp_paths if path['properties']['type'] == 'short'][0]
    s_len = path_s['properties']['length']
    s_noises = path_s['properties']['noises']
    s_th_noises = path_s['properties']['th_noises']
    s_nei = path_s['properties']['nei']
    s_mdB = path_s['properties']['mdB']
    for path in comp_paths:
        props = path['properties']
        path['properties']['noises_diff'] = noise_exps.get_noises_diff(s_noises, props['noises'])
        path['properties']['th_noises_diff'] = noise_exps.get_noises_diff(s_th_noises, props['th_noises'], full_db_range=False)
        path['properties']['len_diff'] = round(props['length'] - s_len, 1)
        path['properties']['len_diff_rat'] = round((path['properties']['len_diff'] / s_len) * 100, 1) if s_len > 0 else 0
        path['properties']['mdB_diff'] = round(props['mdB'] - s_mdB, 1)
        path['properties']['nei_norm'] = round(path['properties']['nei_norm'], 2)
        path['properties']['nei_diff'] = round(path['properties']['nei'] - s_nei, 1)
        path['properties']['nei_diff_rat'] = round((path['properties']['nei_diff'] / s_nei) * 100, 1) if s_nei > 0 else 0
        path['properties']['path_score'] = round((path['properties']['nei_diff'] / path['properties']['len_diff']) * -1, 1) if path['properties']['len_diff'] > 0 else 0
    return comp_paths

def get_quiet_path_dicts_from_qp_df(gdf) -> List[dict]:
    """Converts a GeoDataFrame containing the quiet paths to a list of dicts.
    """
    features = []
    for path in gdf.itertuples():
        feature_d = geom_utils.get_geojson_from_geom(getattr(path, 'geometry'))
        feature_d['properties']['type'] = getattr(path, 'type')
        feature_d['properties']['id'] = getattr(path, 'id')
        feature_d['properties']['length'] = getattr(path, 'total_length')
        feature_d['properties']['noises'] = getattr(path, 'noises')
        feature_d['properties']['noise_pcts'] = getattr(path, 'noise_pcts')
        feature_d['properties']['th_noises'] = getattr(path, 'th_noises')
        feature_d['properties']['mdB'] = getattr(path, 'mdB')
        feature_d['properties']['nei'] = getattr(path, 'nei')
        feature_d['properties']['nei_norm'] = getattr(path, 'nei_norm')
        feature_d['properties']['geometry'] = getattr(path, 'geometry')
        features.append(feature_d)
    return features
