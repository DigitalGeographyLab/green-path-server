import utils.geometry as geom_utils
import utils.noise_exposures as noise_exps

def get_noise_tolerances():
    return [ 0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40 ]

def get_db_costs():
    return { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }

def get_short_quiet_paths_comparison_for_dicts(paths):
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

def get_geojson_from_quiet_paths_gdf(gdf):
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
