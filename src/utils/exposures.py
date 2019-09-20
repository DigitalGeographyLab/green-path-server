import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import ast
import utils.geometry as geom_utils

def add_noises_to_split_lines(noise_polygons, split_lines):
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

def get_exposure_lines(line_geom, noise_polys):
    split_lines = geom_utils.get_split_lines_gdf(line_geom, noise_polys)
    if (split_lines.empty):
        return gpd.GeoDataFrame()
    line_noises = add_noises_to_split_lines(noise_polys, split_lines)
    line_noises = line_noises.fillna(40)
    len_error = abs(line_geom.length - line_noises['length'].sum())
    if (len_error > 0.1):
        print('len_error:', len_error)
        print(' orig geom len:', line_geom.length)
        print(' line noises sum len:', line_noises['length'].sum())
    return line_noises

def get_exposures(line_noises):
    if (len(line_noises.index) == 0):
        return {}
    noise_dict = {}
    noise_groups = line_noises.groupby('db_lo')
    for key, values in noise_groups:
        tot_len = round(values['length'].sum(),3)
        noise_dict[int(key)] = tot_len
    return noise_dict

def get_exposures_for_geom(line_geom, noise_polys):
    line_noises = get_exposure_lines(line_geom, noise_polys)
    return get_exposures(line_noises)

def get_exposure_times(d: 'dict of db: length', speed: 'float: m/s', minutes: bool):
    exp_t_d = {}
    for key in d.keys():
        exp_t_d[key] = round((d[key]/speed)/(60 if minutes else 1), (4 if minutes else 1))
    return exp_t_d

def get_th_exposures(noise_dict, ths):
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

def get_noise_pcts(noise_dict, total_length):
    noise_dists = {}
    db_40_len = round(total_length - get_total_noises_len(noise_dict),1)
    if db_40_len > 0:
        noise_dists[40] = db_40_len
    for noise in noise_dict.keys():
        noise_dist = noise_dict[noise]
        if noise == 45:
            if 40 in noise_dists.keys(): noise_dists[40] += noise_dist
            else: noise_dists[40] = noise_dist
        elif noise >= 70:
            if 70 in noise_dists.keys(): noise_dists[70] += noise_dist
            else: noise_dists[70] = noise_dist
        else:
            noise_dists[noise] = noise_dist
    noise_pcts = {}
    for noise in noise_dists.keys():
        noise_dist = noise_dists[noise]
        noise_pcts[noise] = round(noise_dist*100/total_length, 1)
    return noise_pcts

def get_noise_attrs_to_split_lines(gdf, noise_polys):
    gdf['split_line_index'] = gdf.index
    gdf['geometry'] = gdf['mid_point']
    split_line_noises = gpd.sjoin(gdf, noise_polys, how='left', op='intersects')
    if (len(split_line_noises.index) > len(gdf.index)):
        split_line_noises = split_line_noises.sort_values('db_lo', ascending=False)
        split_line_noises = split_line_noises.drop_duplicates(subset=['split_line_index'], keep='first')
    return split_line_noises

def get_noise_dict_for_geom(geom, noise_polys):
    noise_lines = get_exposure_lines(geom, noise_polys)
    if (noise_lines.empty):
        return {}
    else:
        return get_exposures(noise_lines)

def aggregate_line_noises(split_line_noises, uniq_id):
    row_accumulator = []
    grouped = split_line_noises.groupby(uniq_id)
    for key, values in grouped:
        row_d = {uniq_id: key}
        row_d['noises'] = get_exposures(values)
        row_accumulator.append(row_d)
    return pd.DataFrame(row_accumulator)

def add_noise_exposures_to_gdf(line_gdf, uniq_id, noise_polys):
    # add noises to lines as list
    line_gdf['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in line_gdf['geometry']]
    # explode new rows from split lines column
    split_lines = geom_utils.explode_lines_to_split_lines(line_gdf, uniq_id)
    # join noises to split lines
    split_line_noises = get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to segments
    line_noises = aggregate_line_noises(split_line_noises, uniq_id)
    line_gdf = line_gdf.drop(['split_lines'], axis=1)
    return pd.merge(line_gdf, line_noises, how='inner', on=uniq_id)

def aggregate_exposures(exp_list):
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

def get_noises_diff(s_noises, q_noises, full_db_range=True):
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

def get_total_noises_len(noises):
    totlen = 0
    for key in noises.keys():
        totlen += noises[key]
    return round(totlen, 3)

def get_mean_noise_level(noises: dict, length: float):
    sum_db = 0
    # estimate mean dB of 5 dB range to be min dB + 2.5 dB
    for db in noises.keys():
        sum_db += (int(db)+2.5) * noises[db]
    # extrapolate noise level range 40-45dB (42.5dB) for all noises less than lowest noise range in the noise data 45-50dB
    sum_noise_len = get_total_noises_len(noises)
    db425len = length - sum_noise_len
    sum_db += 42.5 * db425len
    mean_db = sum_db/length
    return round(mean_db, 2)

def get_noise_cost(noises={}, db_costs={}, nt=1):
    noise_cost = 0
    for db in noises:
        if (db in db_costs):
            noise_cost += noises[db] * db_costs[db] * nt
    return round(noise_cost, 2)

def compare_lens_noises_lens(edge_gdf):
    gdf = edge_gdf.copy()
    gdf['uvkey_str'] = [str(uvkey[0])+'_'+str(uvkey[1]) for uvkey in gdf['uvkey']]
    gdf['node_from'] = [uvkey[0] for uvkey in gdf['uvkey']]
    gdf['length'] = [geom.length for geom in gdf['geometry']]
    gdf['len_from_noises'] = [get_total_noises_len(noises) for noises in gdf['noises']]
    gdf['len_noise_error'] = gdf.apply(lambda row: row['length'] - row['len_from_noises'], axis=1)
    return gdf
