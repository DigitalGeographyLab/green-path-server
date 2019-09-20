import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
from shapely.geometry import Point
import utils.geometry as geom_utils
import utils.utils as utils

def group_home_walks(df):
    # calculate probability of taking particular walk from home location based on aggregated utilizations of walks
    grouped_dfs = []
    # group by uniq_id (which is either axyind + PT stop id or axyind + txyind)
    grouped = df.groupby('uniq_id')
    total_utilization_sum = df['utilization'].sum()
    for key, values in grouped:
        firstrow = values.iloc[0]
        g_gdf = pd.DataFrame([firstrow])
        # number of walks
        g_gdf['count'] = len(values.index)
        walk_utilization = values['utilization'].sum()
        g_gdf['utilization'] = round(walk_utilization, 2)
        g_gdf['prob'] = round((walk_utilization/total_utilization_sum)*100, 2)
        grouped_dfs.append(g_gdf)
    origin_stop_groups = pd.concat(grouped_dfs).reset_index(drop=True)
    return origin_stop_groups

def get_walk_uniq_id(row):
    if (row['to_pt_mode'] == 'none'):
        uniq_id = f'''{row['from_axyind']}_{row['to_id']}'''
        return uniq_id
    else:
        uniq_id = f'''{row['from_axyind']}_{row['stop_id']}'''
        return uniq_id
