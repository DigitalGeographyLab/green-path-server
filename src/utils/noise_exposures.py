"""
This module provides various functions for assessing and calculating expsoures to traffic noise. 
The functions are useful in calculating noise costs for quiet path route optimization and in comparing exposures to noise
between paths.

"""

from typing import List, Set, Dict, Tuple
import ast
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import utils.geometry as geom_utils

def calc_db_cost_v2(db) -> float:
    """Returns a noise cost for given dB based on a linear scale (dB >= 45 & dB <= 75).
    """
    if (db <= 40): 
        return 0
    db_cost = (db-40) / (75-40)
    return round(db_cost, 3)

def calc_db_cost_v3(db) -> float:
    """Returns a noise cost for given dB: every 10 dB increase doubles the cost (dB >= 45 & dB <= 75).
    """
    if (db <= 40): return 0
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
    dbs = [45, 50, 55, 60, 65, 70, 75]
    if (version == 1):
        return { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    elif (version == 2):
        return { db: calc_db_cost_v2(db) for db in dbs }
    elif (version == 3):
        return { db: calc_db_cost_v3(db) for db in dbs }
    else:
        raise ValueError('Parameter: version must be either 1, 2 or 3')

def get_noise_sensitivities() -> List[float]:
    """Returns a set of noise sensitivity coefficients that can be used in adding alternative noise-based costs to edges and
    subsequently calculating alternative quiet paths (using different weights for noise cost in routing).

    Args:
        subset: A boolean variable indicating whether a subset of sensitivities should be returned.
    Note:
        The subset should only contain values that are present in the full set as the full set is used to assign the
        cost attributes to the graph.
    Returns:
        A list of noise sensitivity coefficients.
    """
    return [ 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 7, 10 ]

def add_noises_to_split_lines(noise_polygons: gpd.GeoDataFrame, split_lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Performs a spatial join of noise values (from noise polygons) to LineString objects based on
    spatial intersection of the center points of the lines and the noise polygons.

    Note:
        The polygons in the noise_polygons GeoDataFrame should not overlap. However, they sometimes do and hence
        the result of the spatial join needs to be filtered from duplicate noise values for some lines. In removing
        the duplicate noise values, higher noise values are retained. 

    Returns:
        The result of the spatial join as a GeoDataFrame with the added columns from noise polygons (db_lo & db_hi).
    """
    split_lines['split_line_index'] = split_lines.index
    split_lines['geom_line'] = split_lines['geometry']
    split_lines['geom_point'] = [geom_utils.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='intersects')
    line_noises['geometry'] = line_noises['geom_line']
    if (len(line_noises.index) > len(split_lines.index)):
        line_noises = line_noises.sort_values('db_lo', ascending=False)
        line_noises = line_noises.drop_duplicates(subset=['split_line_index'], keep='first')
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]

def get_noise_exposure_lines(line_geom: LineString, noise_polys: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """TODO: check if this is needed anymore.
    """
    split_lines = geom_utils.get_split_lines_gdf(line_geom, noise_polys)
    if (split_lines.empty):
        return gpd.GeoDataFrame()
    line_noises = add_noises_to_split_lines(noise_polys, split_lines)
    line_noises = line_noises.fillna({ 'db_lo': 40 })
    len_error = abs(line_geom.length - line_noises['length'].sum())
    if (len_error > 0.1):
        print('len_error:', len_error)
        print(' orig geom len:', line_geom.length)
        print(' line noises sum len:', line_noises['length'].sum())
    return line_noises

def get_exposures(line_noises: gpd.GeoDataFrame) -> Dict[int, float]:
    """Aggregates exposures (contaminated distances) to different traffic noise levels to a dictionary.
    """
    if (len(line_noises.index) == 0):
        return {}
    noise_dict = {}
    noise_groups = line_noises.groupby('db_lo')
    for key, values in noise_groups:
        tot_len = round(values['length'].sum(),3)
        noise_dict[int(key)] = tot_len
    return noise_dict

def get_th_exposures(noise_dict: dict, ths: List[int]) -> Dict[int, float]:
    """Aggregates exposures to traffic noise levels exceeding the traffic noise levels specified in [ths].
    """
    th_count = len(ths)
    th_lens = [0] * len(ths)
    for th in noise_dict.keys():
        th_len = noise_dict[th]
        for idx in range(th_count):
            if (th >= ths[idx]):
                th_lens[idx] = th_lens[idx] + th_len
    th_noise_dict = {}
    for idx in range(th_count):
        th_noise_dict[ths[idx]] = round(th_lens[idx],3)
    return th_noise_dict

def get_noise_range(dB: float) -> int:
    """Returns the lower limit of one of the six pre-defined dB ranges based on dB.
    """
    if dB >= 70.0: return 70
    elif dB >= 65.0: return 65
    elif dB >= 60.0: return 60
    elif dB >= 55.0: return 55
    elif dB >= 50.0: return 50
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
    noise_dists = dict(noises)
    dB_range_lens = {}
    for dB in noise_dists.keys():
        dB_range = get_noise_range(dB)
        if (dB_range in dB_range_lens.keys()): dB_range_lens[dB_range] += noise_dists[dB]
        else: dB_range_lens[dB_range] = noise_dists[dB]
    
    # round exposures
    dB_range_exps = {}
    for dB_range in dB_range_lens.keys():
        dB_range_exps[dB_range] = round(dB_range_lens[dB_range], 2)

    return dB_range_exps

def get_noise_range_pcts(dB_range_exps: dict, length: float) -> Dict[int, float]:
    """Calculates percentages of aggregated exposures to different noise levels of total length.

    Note:
        Noise levels exceeding 70 dB are aggregated and as well as noise levels lower than 50 dB. 
    Returns:
        A dictionary containing noise level values with respective percentages.
        (e.g. { 50: 35, 60: 65 })
    """
    # calculate ratio (%) of each range's length to total length
    range_pcts = {}
    for dB_range in dB_range_exps.keys():
        range_pcts[dB_range] = round(dB_range_exps[dB_range]*100/length, 1)

    return range_pcts

def get_noise_attrs_to_split_lines(gdf: gpd.GeoDataFrame, noise_polys: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Performs a spatial join of noise values (from noise polygons) to LineString objects based on a
    spatial intersection of the center points of the lines [gdf] and the noise polygons.

    Note:
        The polygons in the noise_polygons GeoDataFrame should not overlap. However, they sometimes do and hence
        the result of the spatial join needs to be filtered from duplicate noise values for some lines. In removing
        the duplicate noise values, higher noise values are retained. 

    Returns:
        The result of the spatial join as a GeoDataFrame with the added columns from noise polygons (db_lo & db_hi).
    """
    gdf['split_line_index'] = gdf.index
    gdf['geometry'] = gdf['mid_point']
    split_line_noises = gpd.sjoin(gdf, noise_polys, how='left', op='intersects')
    if (len(split_line_noises.index) > len(gdf.index)):
        split_line_noises = split_line_noises.sort_values('db_lo', ascending=False)
        split_line_noises = split_line_noises.drop_duplicates(subset=['split_line_index'], keep='first')
    return split_line_noises

def aggregate_line_noises(split_line_noises: gpd.GeoDataFrame, uniq_id: str) -> pd.DataFrame:
    """Aggregates noise exposures (contaminated distances) from lines' noise exposures by unique id. 
    """
    row_accumulator = []
    grouped = split_line_noises.groupby(uniq_id)
    for key, values in grouped:
        row_d = { uniq_id: key }
        row_d['noises'] = get_exposures(values)
        row_accumulator.append(row_d)
    return pd.DataFrame(row_accumulator)

def aggregate_exposures(exp_list: List[dict]) -> Dict[int, float]:
    """Aggregates noise exposures (contaminated distances) from a list of noise exposures. 
    """
    exps = {}
    for exp_d_value in exp_list:
        exp_d = ast.literal_eval(exp_d_value) if type(exp_d_value) == str else exp_d_value
        for db in exp_d.keys():
            if db in exps.keys():
                exps[db] += exp_d[db]
            else:
                exps[db] = exp_d[db]
    for db in exps.keys():
        exps[db] = round(exps[db], 2)
    return exps

def get_noises_diff(s_noises: Dict[int, float], q_noises: Dict[int, float], full_db_range=True) -> Dict[int, float]:
    """Calculates the differences in exposures (contaminated distances) to different noise levels between two noise exposure dictionaries.
    """
    dbs = [40, 45, 50, 55, 60, 65, 70, 75]
    diff_dict = {}
    for db in dbs:
        if (full_db_range == False):
            if((db not in s_noises.keys()) and (db not in q_noises.keys())):
                continue
        s_noise = s_noises[db] if db in s_noises.keys() else 0
        q_noise = q_noises[db] if db in q_noises.keys() else 0
        noise_diff = q_noise - s_noise
        diff_dict[db] = round(noise_diff, 2)
    return diff_dict

def get_total_noises_len(noises: Dict[int, float]) -> float:
    """Returns a total length of exposures to all noise levels.
    """
    totlen = 0
    for key in noises.keys():
        totlen += noises[key]
    return round(totlen, 3)

def get_mean_noise_level(noises: dict, length: float) -> float:
    """Returns a mean noise level based on noise exposures weighted by the contaminated distances to different noise levels.
    """
    sum_db = 0
    # estimate mean dB of 5 dB range to be min dB + 2.5 dB
    for db in noises.keys():
        sum_db += (int(db)+2.5) * noises[db]
    mean_db = sum_db/length
    return round(mean_db, 1)

def get_noise_cost(noises: Dict[int, float] = {}, db_costs: Dict[int, float] = {}, sen: float = 1) -> float:
    """Returns a total noise cost based on contaminated distances to different noise levels, db_costs and noise sensitivity. 
    """
    noise_cost = 0
    for db in noises:
        if (db in db_costs):
            noise_cost += noises[db] * db_costs[db] * sen
    return round(noise_cost, 2)

def interpolate_link_noises(link_len_ratio: float, link_geom: LineString, edge_geom: LineString, edge_noises: dict) -> dict:
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
    cost_attrs = {}
    # estimate link costs based on link length - edge length -ratio and edge noises
    link_len_ratio = link_geom.length / edge_dict['geometry'].length
    cost_attrs['noises'] = interpolate_link_noises(link_len_ratio, link_geom, edge_dict['geometry'], edge_dict['noises'])
    # calculate noise sensitivity specific noise costs
    for sen in sens:
        noise_cost = get_noise_cost(noises=cost_attrs['noises'], db_costs=db_costs, sen=sen)
        cost_attrs['nc_'+str(sen)] = round(noise_cost + link_geom.length, 2)
    return cost_attrs

def estimate_db_40_exp(noises: dict, length: float) -> float:
    total_db_length = get_total_noises_len(noises)
    return round(length - total_db_length, 2)

def compare_lens_noises_lens(edge_gdf) -> gpd.GeoDataFrame:
    """Adds new columns to a GeoDataFrame of edges so that the aggregated contaminated distances can be validated against edge lengths. 
    """
    gdf = edge_gdf.copy()
    gdf['uvkey_str'] = [str(uvkey[0])+'_'+str(uvkey[1]) for uvkey in gdf['uvkey']]
    gdf['node_from'] = [uvkey[0] for uvkey in gdf['uvkey']]
    gdf['length'] = [geom.length for geom in gdf['geometry']]
    gdf['len_from_noises'] = [get_total_noises_len(noises) for noises in gdf['noises']]
    gdf['len_noise_error'] = gdf.apply(lambda row: row['length'] - row['len_from_noises'], axis=1)
    return gdf
