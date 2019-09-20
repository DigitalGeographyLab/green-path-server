import pandas as pd
import geopandas as gpd
import numpy as np
import statistics as stats
import utils.files as files
import utils.geometry as geom_utils

def add_bool_within_hel_poly(gdf):
    # read city extent (polygon of Helsinki)
    hel_poly = files.get_hel_poly()
    hel_poly.buffer(30)
    # hel_poly = geom_utils.project_to_wgs(hel_poly)
    def inside_hel_extent(geometry):
        return 'yes' if geometry.within(hel_poly) else 'no'
    gdf['b_inside_hel'] = [inside_hel_extent(geom) for geom in gdf['geometry']]
    in_out_array = gdf['b_inside_hel']
    inside_count = len([x for x in in_out_array if x == 'yes'])
    outside_count = len([x for x in in_out_array if x == 'no'])
    print('count inside:', inside_count)
    print('count outside:', outside_count)
    return gdf

def fix_dt_len_diff(df):
    paths = df.copy()
    paths['DT_len_diff_rat'] = paths.apply(lambda row: round((row['DT_len_diff']/row['DT_len'])*100,2), axis=1)
    return paths

def map_pt_path_props_to_null(df):
    paths = df.copy()
    print('PT_path_walk_paths', len(paths.query("to_pt_mode == 'WALK'")))
    paths['length'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['length'], axis=1)
    paths['mdB'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['mdB'], axis=1)
    paths['nei'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['nei'], axis=1)
    paths['nei_norm'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['nei_norm'], axis=1)
    paths['DT_len'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['DT_len'], axis=1)
    paths['DT_len_diff'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['DT_len_diff'], axis=1)
    paths['DT_len_diff_rat'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['DT_len_diff_rat'], axis=1)
    paths['noises'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['noises'], axis=1)
    paths['th_noises'] = paths.apply(lambda row: -9999 if row['to_pt_mode'] == 'WALK' else row['th_noises'], axis=1)
    print('mapped', len(paths.query("length == -9999")), 'lengths to -9999')
    return paths

def extract_th_db_cols(paths_gdf, ths=[60, 65], valueignore=-9999, add_ratios=True):
    gdf = paths_gdf.copy()
    def get_db_len_ratio(row, th_len_col):
        if (row['length'] == valueignore):
            return valueignore
        return round((row[th_len_col]/row['length'])*100,2)
    
    for th in ths:
        th_key = str(th)
        th_col = str(th)+'dBl'
        gdf[th_col] = [th_noises[th_key] if type(th_noises) == dict else valueignore for th_noises in gdf['th_noises']]
    if (add_ratios == True):
        for th in ths:
            th_len_col = str(th)+'dBl'
            th_rat_col = str(th)+'dBr'
            gdf[th_rat_col] = gdf.apply(lambda row: get_db_len_ratio(row, th_len_col), axis=1)
    print('mapped', len(gdf[gdf['60dBl'] == valueignore]), 'db stats to -9999')
    return gdf

def add_dt_length_diff_cols(paths_gdf, valueignore=-9999):
    gdf = paths_gdf.copy()
    def get_reference_len_rat(row):
        return round((row['DT_len_diff']/row['length'])*100,2)
    gdf['DT_len_diff_rat'] = gdf.apply(lambda row: get_reference_len_rat(row) if row['DT_len_diff'] != valueignore else valueignore, axis=1)
    print('mapped', len(gdf[gdf['DT_len_diff_rat'] == valueignore]), 'length stats to -9999')
    return gdf

def explode_array_by_weights(df, var_col, weight_col):
    orig_array = df[var_col]
    weights = df[weight_col]
    if (len(orig_array) != len(weights)):
        print('length of weights does not match the length of values')
    expl_array = []
    for val, weight in zip(orig_array, weights):
        expl_array += [val] * int(round(weight*10))
    return expl_array

def filter_by_min_value(data_df, var_col, min_value):
    df = data_df.copy()
    count_before = len(df)
    df = df.query(f'''{var_col} > {min_value}''')
    count_after = len(df)
    print('Filtered out:', count_before-count_after, 'paths with:', var_col, 'lower than:', min_value)
    return df

def filter_by_max_value(data_df, var_col, max_value):
    df = data_df.copy()
    count_before = len(df)
    df = df.query(f'''{var_col} < {max_value}''')
    count_after = len(df)
    print('Filtered out:', count_before-count_after, 'paths with:', var_col, 'higher than:', max_value)
    return df

def filter_out_problem_paths(data_df, printing=False):
    df = data_df.copy()
    count_before = len(df)
    df = df.query('orig_offset < 110')
    count_after = len(df)
    if (printing == True): print('Filtered out:', count_before-count_after, 'paths of:', count_before, 'with: orig_offset < 110')
    return df

def calc_basic_stats(data_gdf, var_col, valuemap=None, valueignore=None, axyindsignore=None, weight=None, minmax=False, min_length=None, percs=None, col_prefix='', printing=False, add_varname=False, add_n=False):
    gdf = data_gdf.copy()
    if (printing == True): print('\n-min_length:', min_length, '-weight:', weight, '-col:', var_col)
    
    # filter out paths from problematic axyinds (if given)
    if (axyindsignore is not None):
        count_before = len(gdf)
        for axyind in axyindsignore:
            gdf = gdf[gdf['from_axyind'] != axyind]
        count_after = len(gdf)
        if (printing == True): print('Filtered out:', count_before-count_after, 'paths from problematic axyinds')

    if (valueignore is not None):
        count_before = len(gdf)
        gdf = gdf[gdf[var_col] != valueignore]
        count_after = len(gdf)
        if (printing == True): print('Filtered out:', count_before-count_after, 'with value:', valueignore, 'total rows after filter:', count_after)
    
    if (min_length is not None):
        count_before = len(gdf)
        gdf = gdf.query(f'''length > {min_length}''')
        count_after = len(gdf)
        if (printing == True): print('Filtered out:', count_before-count_after, 'paths shorter than', min_length, 'm')
    
    n = len(gdf.index)
    if (printing == True): print('n=', n)
    
    var_array = []
    if (weight is not None):
        if (printing == True): print('Weighted stats:')
        var_array = explode_array_by_weights(gdf, var_col, weight)
    else:
        if (printing == True): print('Basic stats:')
        var_array = gdf[var_col]

    if (valuemap is not None):
        var_array = [value if value != valuemap[0] else valuemap[1] for value in var_array]

    mean = round(np.mean(var_array), 3)
    std = round(np.std(var_array), 3)
    median = round(np.median(var_array), 3)

    col_name = col_prefix +'_' if (col_prefix is not '' and add_varname != True) else ''
    d = { 'name': col_prefix if col_prefix != '' else var_col } if (add_varname == True) else {}
    if (add_n == True): d['n'] = n
    d = { **d, col_name+'mean': mean, col_name+'median': median, col_name+'std': std }

    if (percs is not None):
        for per in percs:
            d['p'+str(per)] = np.percentile(var_array, per)

    if (minmax == True):
        d['min'] = round(np.min(var_array), 3)
        d['max'] = round(np.max(var_array), 3)

    if (printing == True): print('STATS:', d)

    return d

def get_best_quiet_paths_of_max_len_diffs(od_id=None, df=None, sp=None, max_len_diffs=None):
    # od_qp_stats = {'od_id': od_id, 'length': sp['length'], 'nei_norm': sp['nei_norm'], 'util': sp['util'] }
    qp_stats = {}
    for max_len in max_len_diffs:
        qps = df.query(f'''len_diff < {max_len}''')
        found_qps = len(qps) > 0
        qps = qps.sort_values('len_diff', ascending=False) if found_qps == True else None
        qp = qps.to_dict(orient='records')[0] if found_qps == True else {}
        # od_qp_stats['len_qp'+str(max_len)] = qp['length'] if found_qps == True else -9999
        qp_stats['len_diff_qp'+str(max_len)] = qp['len_diff'] if found_qps == True else -9999
        qp_stats['len_diff_r_qp'+str(max_len)] = qp['len_diff_r'] if found_qps == True else -9999
        qp_stats['nei_qp'+str(max_len)] = qp['nei_norm'] if found_qps == True else -9999
        qp_stats['nei_diff_qp'+str(max_len)] = qp['nei_diff'] if found_qps == True else -9999
        qp_stats['nei_diff_r_qp'+str(max_len)] = qp['nei_diff_r'] if found_qps == True else -9999
        qp_stats['mdB_diff_qp'+str(max_len)] = qp['mdB_diff'] if found_qps == True else -9999
        qp_stats['60dB_diff_qp'+str(max_len)] = qp['60dB_diff'] if found_qps == True else -9999
        qp_stats['65dB_diff_qp'+str(max_len)] = qp['65dB_diff'] if found_qps == True else -9999
        qp_stats['60dB_diff_r_qp'+str(max_len)] = qp['60dB_diff_r'] if found_qps == True else -9999
        qp_stats['65dB_diff_r_qp'+str(max_len)] = qp['65dB_diff_r'] if found_qps == True else -9999
    return qp_stats

def filter_out_paths_outside_hel(paths):
    gdf = paths.copy()
    gdf = add_bool_within_hel_poly(gdf)
    gdf_filt = gdf.query("b_inside_hel == 'yes'")
    print('Filtered out:', len(gdf)-len(gdf_filt), 'paths outside hel -', round(100*(len(gdf)-len(gdf_filt))/len(gdf), 1), '%')
    return gdf_filt

def filter_out_paths_from_axyinds(paths, axyinds: list):
    gdf = paths.copy()
    gdf_filt = gdf[~gdf['from_axyind'].isin(axyinds)]
    print('Filtered out:', len(gdf)-len(gdf_filt), 'paths from axyinds -', round(100*(len(gdf)-len(gdf_filt))/len(gdf), 1), '%')
    return gdf_filt

def filter_out_null_paths(paths, null_val=-9999):
    gdf = paths.copy()
    gdf_filt = gdf.query(f'''length != {null_val}''')
    print('Filtered out:', len(gdf)-len(gdf_filt), 'null paths -', round(100*(len(gdf)-len(gdf_filt))/len(gdf), 1), '%')
    return gdf_filt
