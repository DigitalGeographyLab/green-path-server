from typing import Any, List, Union
from pandas import DataFrame
from common.igraph import Edge as E
from geopandas import GeoDataFrame
from shapely.geometry import LineString
from logging import Logger
from enum import Enum
import common.igraph as ig_utils
import rasterio
import pandas as pd
import numpy as np


def get_sampling_point_gdf_from_graph(graph) -> GeoDataFrame:
    """Creates GeoDataFrame of edges of the graph. Filters out null geometries and
    adds point geometries to be used as sampling points.
    """
    edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.id_way], geom_attr=E.geom_wgs)
    # filter out edges with null geometry
    edge_gdf = edge_gdf[edge_gdf[E.geom_wgs.name].apply(lambda x: isinstance(x, LineString))]
    edge_gdf['point_geom'] = [geom.interpolate(0.5, normalized=True) for geom in edge_gdf[E.geom_wgs.name]]
    return edge_gdf


def round_coordinates(coords_list: List[tuple], digits=6) -> List[tuple]:
    return [
        (round(coords[0], digits), round(coords[1], digits)) 
        for coords in coords_list
    ]


def sample_aq_to_point_gdf(
    sampling_gdf: GeoDataFrame,
    aq_tif_file: str,
    aq_attr_name: str
) -> GeoDataFrame:
    """Joins AQI values from an AQI raster file to edges (edge_gdf) of a graph by spatial sampling. 
    Column 'aqi' will be added to the G.edge_gdf. Center points of the edges are used in the spatial join. 
    Exports a csv file of ege keys and corresponding AQI values to use for updating AQI values to a graph.

    Args:
        G: A GraphHandler object that has edge_gdf and graph as properties.
        aqi_tif_name: The filename of an AQI raster (GeoTiff) file (in aqi_cache directory).
    Todo:
        Implement more precise join for longer edges. 
    Returns:
        The name of the exported csv file (e.g. aqi_2019-11-08T14.csv).
    """
    gdf = sampling_gdf.copy()
    aqi_raster = rasterio.open(aq_tif_file)
    # get coordinates of edge centers as list of tuples
    coords = [
        (x, y) for x, y 
        in zip(
            [point.x for point in gdf['point_geom']],
            [point.y for point in gdf['point_geom']]
        )
    ]
    coords = round_coordinates(coords)
    # extract aqi values at coordinates from raster using sample method from rasterio
    gdf[aq_attr_name] = [round(x.item(), 2) for x in aqi_raster.sample(coords)]
    return gdf


def validate_aqi_sample_df(df: DataFrame, log: Logger = None) -> DataFrame:
    """Validates sampled AQI values. Prints error if invalid values are found
    and returns the dataframe where invalid AQI values are replaced with np.nan. 
    """
    if not validate_aqi_samples(list(df['aqi']), log):
        if log: log.error('AQI sampling failed')

    df['aqi'] = [get_valid_aqi_or_nan(aqi) for aqi in df['aqi']]
    return df


def merge_edge_aq_samples(
    edge_gdf: GeoDataFrame, 
    aqi_sample_df: GeoDataFrame,
    aq_attr: str = 'aqi',
    log: Logger = None
) -> GeoDataFrame:
    """Merges sampled AQI values to all edges (GDF). Merging is needed as the sample GDF consists
    of only unique edge geometries. 
    """
    edge_gdf_copy = edge_gdf[[E.id_ig.name, E.id_way.name]].copy()
    final_sample_df = pd.merge(
        edge_gdf_copy, 
        aqi_sample_df[[E.id_way.name, aq_attr]],
        on=E.id_way.name, how='left'
    )
    sample_count_all = len(final_sample_df)
    final_sample_df = final_sample_df[final_sample_df[aq_attr].notnull()]

    if log:
        ok_samples_share = round(100 * len(final_sample_df)/sample_count_all, 2)
        log.info(f'Found valid AQI samples for {ok_samples_share} % edges')
    
    return final_sample_df[[E.id_ig.name, aq_attr]]


class AqiValidity(Enum):
    OK = 0
    Missing = 1
    UnderOne = 2
    UnderZero = 3
    WrongType = 4


def get_valid_aqi_or_nan(aqi: Union[float, Any]):
    """Returns np.nan for invalid or missing AQI, else returns the AQI. 
    """
    if not isinstance(aqi, float):
        return np.nan
    
    if np.isfinite(aqi):
        if aqi < 0.95:
            return np.nan
        elif aqi < 1:
            return 1.0
        else:
            return aqi
    else:
        return np.nan


def validate_aqi_exp(aqi: Union[float, Any]) -> AqiValidity:
    if not isinstance(aqi, float):
        return AqiValidity.WrongType
    elif aqi < 0:
        return AqiValidity.UnderZero
    elif aqi == 0.0:
        return AqiValidity.Missing
    elif aqi < 1:
        return AqiValidity.UnderOne
    else:
        return AqiValidity.OK


def validate_aqi_samples(
    aqi_samples: List[Union[float, Any]],
    log: Logger = None
) -> bool:
    """Validates list of sampled AQI values. Returns True if all AQI values are either missing or valid, 
    else returns False. 
    """

    sample_count = len(aqi_samples)
    aqi_validities = [validate_aqi_exp(aqi) for aqi in aqi_samples]
    aqi_ok_count = len(
        [aqi_v for aqi_v in aqi_validities if aqi_v.value <= AqiValidity.Missing.value]
    )
    
    invalid_count = sample_count - aqi_ok_count
    if invalid_count:
        invalid_ratio = round(100 * invalid_count/sample_count, 2)
        if log: 
            log.warning(
                f'AQI sample count: {sample_count} of which has invvalid AQI: '
                f'{invalid_count} = {invalid_ratio}  %'
            )
        return False

    return True
