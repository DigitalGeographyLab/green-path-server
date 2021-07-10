import geopandas as gpd
import numpy as np
import pandas as pd
from statistics import mode
from collections import Counter
from common.igraph import Edge
from shapely.geometry import LineString, Point
from graph_build.graph_noise_join.schema import SamplingGdf as S
from pyproj import CRS
from typing import List


def get_point_sampling_distances(sample_count: int) -> List[float]:
    """Calculates set of distances for sample points as relative shares.
    """
    sampling_interval = 1/sample_count
    sp_indexes = range(0, sample_count)
    sample_distances = [sampling_interval/2 + sp_index * sampling_interval for sp_index in sp_indexes]
    return sample_distances


def get_sampling_points(geom: LineString, sampling_interval: int) -> List[Point]:
    """Finds and returns sample points as Point objects for a LineString object (geom). Sampling interval (m) is 
    given as argument sampling_interval.  
    """
    sample_count = round(geom.length / sampling_interval)
    sample_count = sample_count if sample_count != 0 else 1
    sample_distances = get_point_sampling_distances(sample_count)
    return [geom.interpolate(distance, normalized=True) for distance in sample_distances]


def add_sampling_points_to_gdf(gdf, sampling_interval: int) -> gpd.GeoDataFrame:
    """Adds new column S.sampling_points with sampling points by specified interval (m) (sampling_interval).
    """
    gdf[S.sampling_points] = [get_sampling_points(geom, sampling_interval) if isinstance(geom, LineString) else None for geom in gdf[S.geometry].values]
    return gdf


def explode_sampling_point_gdf(gdf, points_geom_column: str) -> gpd.GeoDataFrame:
    """Exploads new rows from dataframe by lists of sampling points. Also adds new column sample_len that
    it is calculated simply by dividing the length of the edge by the number of sampling points for it.
    """
    row_accumulator = []

    def explode_by_sampling_points(row):
        if row[points_geom_column] is not None:
            point_count = len(row[points_geom_column])
            sampling_interval = round(row[S.geometry].length/point_count, 10)
            for point_geom in row[points_geom_column]:
                new_row = {}
                new_row[S.edge_id] = row.name
                new_row[S.sample_len] = sampling_interval
                new_row[S.geometry] = point_geom
                row_accumulator.append(new_row)

    gdf.apply(explode_by_sampling_points, axis=1)
    point_gdf = gpd.GeoDataFrame(row_accumulator, crs=CRS.from_epsg(3879))
    return point_gdf


def add_unique_geom_id(point_gdf: gpd.GeoDataFrame, log=None) -> gpd.GeoDataFrame:
    """Adds an unique identifier (string) to GeoDataFrame of points based on point locations (x/y).
    """
    point_gdf[S.xy_id] = [f'{str(round(geom.x, 1))}_{str(round(geom.y, 1))}' for geom in point_gdf[S.geometry]]
    unique_count = point_gdf[S.xy_id].nunique()
    unique_share = round(100 * unique_count/len(point_gdf.index), 2)
    log.info(f'found {unique_count} unique sampling points ({unique_share} %)')
    return point_gdf


def all_noise_values_none(row, noise_layers: list) -> bool:
    return all([np.isnan(row[layer]) for layer in noise_layers])


def log_none_noise_stats(log, gdf: gpd.GeoDataFrame) -> None:
    missing_count = len(gdf[gdf[S.no_noise_values] == True])
    missing_ratio = round(100 * missing_count/len(gdf.index), 2)
    log.info(f'found {missing_count} ({missing_ratio} %) sampling points without noise values')


def add_inside_nodata_zone_column(gdf, nodata_zone: gpd.GeoDataFrame, log=None) -> gpd.GeoDataFrame:
    """Adds boolean column (nodata_zone) indicating whether the points in the gdf are within the given nodata_zone polygon.

    Args:
        gdf: A GeoDataFrame object of sampling points. 
        nodata_zone: A GeoDataFrame object with one feature in it. It must have one attribute (nodata_zone) with value 1.
    """
    joined = gpd.sjoin(gdf, nodata_zone, how='left', op='within').drop(['index_right'], axis=1)
    if log:
        nodata_zone_count = len(joined[joined[S.nodata_zone] == 1])
        nodata_zone_share = round(100 * nodata_zone_count/len(gdf.index), 2)
        log.info(f'found {nodata_zone_count} ({nodata_zone_share} %) sampling points inside potential nodata zone')
    return joined


def get_sampling_points_around(point: Point, distance: float, count: int=20) -> List[Point]:
    """Returns a set of sampling points at specified distance around a given point.
    """
    buffer = point.buffer(distance)
    boundary = buffer.boundary
    sampling_distances = get_point_sampling_distances(count)
    sampling_points = [boundary.interpolate(dist, normalized=True) for dist in sampling_distances]
    return sampling_points


def explode_offset_sampling_point_gdf(gdf, points_geom_column: str) -> gpd.GeoDataFrame:
    """Explodes dataframe by column containing alternative sampling points for each row.
    """
    row_accumulator = []
    def explode_sampling_point_rows(row):
        for point in row[points_geom_column]:
            new_row = row.to_dict()
            del new_row[points_geom_column]
            new_row[S.geometry] = point
            row_accumulator.append(new_row)

    gdf.apply(explode_sampling_point_rows, axis=1)
    return gpd.GeoDataFrame(row_accumulator, crs=CRS.from_epsg(3879))


def remove_duplicate_samples(sample_gdf, sample_idx: str, noise_layers: dict) -> gpd.GeoDataFrame:
    """Removes duplicate rows generated in spatially joining noise surface values to sampling points. In some cases,
    two or more (invalid) noise surfaces are overlapping each other and thus causing multiple samples at some locations.
    For duplicate samples, the function persists highest values of sampled noise layers. The function keeps the column
    structure of the given GeoDataFrame.
    """
    duplicate_df = sample_gdf[sample_gdf.duplicated([sample_idx], keep=False)]

    if (len(duplicate_df) == 0):
        return sample_gdf

    deduplicated = []
    samples_by_id = duplicate_df.groupby(by=sample_idx)
    for sample_id, samples in samples_by_id:
        # get first row as dictionary
        distinct_sample = samples[:1].to_dict('records')[0]
        # use maximum noise values from overlapping (invalid) noise surfaces
        noise_values = {name: samples[name].max() for name in noise_layers.keys()}
        distinct_sample.update(noise_values)
        deduplicated.append(distinct_sample)

    deduplicated_samples_gdf = gpd.GeoDataFrame(deduplicated, crs=CRS.from_epsg(3879))

    distinct_samples_gdf = sample_gdf.drop_duplicates([sample_idx], keep=False)
    # order columns to match original column order
    deduplicated_samples_gdf = deduplicated_samples_gdf[list(distinct_samples_gdf.columns)]

    # concatenate distinct and deduplicated samples
    concatenated_df = pd.concat([distinct_samples_gdf, deduplicated_samples_gdf], ignore_index=True)
    return gpd.GeoDataFrame(concatenated_df, crs=CRS.from_epsg(3879))


def sjoin_noise_values(gdf, noise_layers: dict, log=None) -> gpd.GeoDataFrame:
    sample_gdf = gdf.copy()
    sample_gdf['sample_idx'] = sample_gdf.index
    for name, noise_gdf in noise_layers.items():
        log.debug(f'joining noise layer [{name}] to sampling points')
        sample_gdf = gpd.sjoin(sample_gdf, noise_gdf, how='left', op='within').drop(['index_right'], axis=1)

    if (len(sample_gdf.index) > len(gdf.index)):
        log.warning(f'joined multiple noise values for one or more sampling points ({len(sample_gdf.index)} != {len(gdf.index)})')

    distinct_samples = remove_duplicate_samples(sample_gdf, 'sample_idx', noise_layers)

    if (len(distinct_samples.index) == len(gdf.index)):
        log.info('successfully removed duplicate samples')
    else:
        log.error('error in removing duplicate samples')

    if (list(sample_gdf.columns).sort() != list(distinct_samples.columns).sort()):
        log.error('schema of the dataframe was altered during removing duplicate samples')

    return distinct_samples.drop(columns=['sample_idx'])


def aggregate_noise_values(sample_gdf, prefer_syke: bool = False) -> gpd.GeoDataFrame:

    # 1) select noise value for each source (type)
    road_columns = [S.hel_road, S.hel_hway, S.espoo_road, S.espoo_hway, S.syke_road, S.syke_hway]
    train_columns = [S.hel_train, S.espoo_train, S.syke_train]
    tram_columns = [S.hel_tram, S.syke_tram]
    metro_columns = [S.hel_metro, S.syke_metro]

    # reorder column names if syke is the preferred noise data
    if prefer_syke:
        road_columns = [S.syke_road, S.syke_hway, S.hel_road, S.hel_hway, S.espoo_road, S.espoo_hway]
        train_columns = [S.syke_train, S.hel_train, S.espoo_train]
        tram_columns = [S.syke_tram, S.hel_tram]
        metro_columns = [S.syke_metro, S.hel_metro]

    def get_first_non_nan_or_nan(row, columns: list) -> float:
        for col in columns:
            if np.isfinite(row[col]): return row[col]
        return np.nan

    sample_gdf[S.road] = sample_gdf.apply(lambda row: get_first_non_nan_or_nan(row, road_columns), axis=1)
    sample_gdf[S.train] = sample_gdf.apply(lambda row: get_first_non_nan_or_nan(row, train_columns), axis=1)
    sample_gdf[S.tram] = sample_gdf.apply(lambda row: get_first_non_nan_or_nan(row, tram_columns), axis=1)
    sample_gdf[S.metro] = sample_gdf.apply(lambda row: get_first_non_nan_or_nan(row, metro_columns), axis=1)

    # 2) add maximum noise value among rail noise sources (TODO decide if this is needed after all?)
    rail_columns = [S.train, S.tram, S.metro]
    sample_gdf[S.rail] = sample_gdf[rail_columns].max(axis=1)

    # 3) add maximum noise value among different sources
    def get_max_noise_value(row, columns: list) -> float:
        values = [row[col] for col in columns if np.isfinite(row[col])]
        return np.nanmax(values) if values else np.nan

    noise_columns = [S.road, S.train, S.tram, S.metro]
    sample_gdf[S.n_max] = sample_gdf.apply(lambda row: get_max_noise_value(row, noise_columns), axis=1)

    # 4) add name(s) of noise sources of maximum noise values
    def get_sources_of_max_noise(row, columns: list) -> tuple:
        """Returns list of names of the noise sources that have the maximum noise value.
        """
        if np.isfinite(row[S.n_max]):
            max_noise = row[S.n_max]
            values = [row[col] for col in columns]
            # if the max noise value is only by one source, return the name of it
            if (values.count(max_noise) == 1):
                return [columns[values.index(max_noise)]]
            else:
                source_indexes = [i for i in range(len(values)) if values[i] == max_noise]
                return [columns[i] for i in source_indexes]
        else:
            return []

    sample_gdf[S.n_max_sources] = sample_gdf.apply(lambda row: get_sources_of_max_noise(row, noise_columns), axis=1)

    # 5) adjust max noises based on number of max noise sources
    def get_adjusted_max_noise(row) -> float:
        """Returns the max noise value if it is based on only one noise source. If many noise sources cause the max noise value, 
        adjusts the max noise value by adding decibels by the count of noise sources.
        """
        if row[S.n_max_sources]:
            add_db = len(row[S.n_max_sources]) if len(row[S.n_max_sources]) > 1 else 0
            return row[S.n_max] + add_db
        else:
            return np.nan

    sample_gdf[S.n_max_adj] = sample_gdf.apply(lambda row: get_adjusted_max_noise(row), axis=1)
    return sample_gdf


def aggregate_noises_by_edge(sample_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Calculates edge-level noise attributes (noises & noise_sources) from sampling points.
    e.g. noises = { 45: 13.2, 50: 22.1 }, noise_source = 'train' & noise_sources = { 'road': 3, 'train', 6 }
    """
    agg_columns = [S.edge_id, S.n_max_adj, S.n_max_sources, S.sample_len]
    out_columns = [S.edge_id, Edge.noises.name, Edge.noise_source.name, Edge.noise_sources.name]

    edge_noises = sample_gdf[agg_columns].groupby(S.edge_id).agg(
        db_counts=(S.n_max_adj, lambda x: x.value_counts().to_dict()),
        sources=(S.n_max_sources, 'sum'),
        sample_len=(S.sample_len, 'median')
        ).reset_index()

    def calculate_noise_exposures(row):
        """Calculates dB specific noise exposures from dB counts, e.g. -> { 45: 13.2, 50: 22.1 }"""
        if row['db_counts']:
            return {int(db): round(count * row[S.sample_len], 5) for db, count in row['db_counts'].items()}
        else:
            return {}

    edge_noises[Edge.noises.name] = edge_noises.apply(lambda row: calculate_noise_exposures(row), axis=1)

    def get_main_noise_source(row) -> str:
        """Returns the most frequent noise source of the edge or '' if it does not have noise sources.
        """
        if row['sources']:
            return mode(row['sources'])
        else:
            return ''

    def calculate_noise_source_counts(row) -> dict:
        """e.g. -> { 'road': 3, 'train': 6 }"""
        if row['sources']:
            sources = Counter(row['sources']).keys()
            counts = Counter(row['sources']).values()
            return dict(zip(sources, counts))
        else:
            return {}

    edge_noises[Edge.noise_source.name] = edge_noises.apply(lambda row: get_main_noise_source(row), axis=1)
    edge_noises[Edge.noise_sources.name] = edge_noises.apply(lambda row: calculate_noise_source_counts(row), axis=1)
    return edge_noises[out_columns]
