import logging
import os
import fiona
import math
from pyproj import CRS
import numpy as np
import pandas as pd
import geopandas as gpd
import graph_build.graph_noise_join.utils as utils
import common.igraph as ig_utils
from common.igraph import Edge as E
from graph_build.graph_noise_join.schema import SamplingGdf as S
from typing import Dict


log = logging.getLogger('noise_graph_join')


def noise_graph_join(
    edge_gdf: gpd.GeoDataFrame,
    sampling_interval: float,
    noise_layers: Dict[str, gpd.GeoDataFrame],
    nodata_layer: gpd.GeoDataFrame,
    b_debug: bool = False,
    debug_gpkg: str = ''
) -> gpd.GeoDataFrame:

    # create sampling points
    edge_gdf = utils.add_sampling_points_to_gdf(edge_gdf, sampling_interval=sampling_interval)
    point_gdf = utils.explode_sampling_point_gdf(edge_gdf, points_geom_column=S.sampling_points)

    # select only unique sampling points for sampling
    point_gdf = utils.add_unique_geom_id(point_gdf, log)
    uniq_point_gdf = point_gdf.drop_duplicates(S.xy_id, keep='first')
    initial_sampling_count = len(uniq_point_gdf.index)
    log.info(f'created {len(uniq_point_gdf)} unique sampling points ({round(len(point_gdf)/point_gdf[S.edge_id].nunique(),2)} per edge)')

    # add boolean column indicating wether sampling point is within potential nodata zone
    uniq_point_gdf = utils.add_inside_nodata_zone_column(uniq_point_gdf, nodata_layer, log)
    # columns: edge_id, sample_len, xy_id, nodata_zone (1 / na)

    if b_debug:
        if os.path.exists(debug_gpkg):
            os.remove(debug_gpkg)
        log.info('exporting edges and sampling points for debugging')
        edge_gdf.drop(columns=[S.sampling_points]).to_file(debug_gpkg, layer='graph_edges', driver='GPKG')
        uniq_point_gdf.to_file(debug_gpkg, layer='sampling_points', driver='GPKG')

    # spatially join noise values by sampling points from a set of noise surface layers
    noise_samples = utils.sjoin_noise_values(uniq_point_gdf, noise_layers, log)

    noise_samples[S.no_noise_values] = noise_samples.apply(lambda row: utils.all_noise_values_none(row, noise_layers), axis=1)
    utils.log_none_noise_stats(log, noise_samples)

    # add column indicating wether sampling points is both located in potential nodata_zone and is missing noise values
    noise_samples[S.missing_noises] = noise_samples.apply(lambda row: True if (row[S.nodata_zone] == 1) & (row[S.no_noise_values] == True) else False, axis=1)
    normal_samples = noise_samples[noise_samples[S.missing_noises] == False].copy()

    if b_debug:
        noise_samples.to_file(debug_gpkg, layer='sampling_points_noise', driver='GPKG')

    missing_noises_count = len(noise_samples[noise_samples[S.missing_noises] == True])
    missing_share = round(100 * missing_noises_count/len(noise_samples.index), 2)
    log.info(f'found {missing_noises_count} ({missing_share} %) sampling points for which noise values need to be interpolated')

    # define columns for sampled values
    sampling_columns = [S.xy_id, S.road, S.train, S.tram, S.metro, S.n_max, S.n_max_sources, S.n_max_adj]

    if missing_noises_count == 0:
        log.info('processing noise samples')
        all_samples = utils.aggregate_noise_values(normal_samples)
        all_samples = all_samples[sampling_columns]
    else:
        # interpolate noise values for sampling points missing them in nodata zones
        interpolated_samples = noise_samples[noise_samples[S.missing_noises] == True][[S.xy_id, S.geometry]].copy()
        interpolated_samples[S.offset_sampling_points] = [utils.get_sampling_points_around(point, distance=7, count=20) for point in interpolated_samples[S.geometry]]
        offset_sampling_points = utils.explode_offset_sampling_point_gdf(interpolated_samples, S.offset_sampling_points)

        if b_debug:
            offset_sampling_points.to_file(debug_gpkg, layer='offset_sampling_points', driver='GPKG')

        # join noise values to offset sampling points
        offset_sampling_point_noises = utils.sjoin_noise_values(offset_sampling_points, noise_layers, log)

        if b_debug:
            offset_sampling_point_noises.to_file(debug_gpkg, layer='offset_sampling_point_noises', driver='GPKG')

        # calculate average noise values per xy_id from offset sampling points
        offset_samples_by_xy_id = offset_sampling_point_noises.groupby(by=S.xy_id)
        row_accumulator = []
        for xy_id, group in offset_samples_by_xy_id:
            samples = group.copy()
            samples = samples.fillna(0)
            interpolated_sample = {name: samples[name].quantile(.7, interpolation='nearest') for name in noise_layers.keys()}
            interpolated_sample[S.xy_id] = xy_id
            row_accumulator.append(interpolated_sample)

        interpolated_noise_samples = pd.DataFrame(row_accumulator)
        interpolated_noise_samples = interpolated_noise_samples.replace(0, np.nan)

        # add newly sampled noise values to sampling points missing them
        interpolated_samples = pd.merge(interpolated_samples.drop(columns=[S.offset_sampling_points]), interpolated_noise_samples, on=S.xy_id, how='left')
        if b_debug:
            interpolated_samples.to_file(debug_gpkg, layer='interpolated_samples', driver='GPKG')

        # add maximum noise values etc. to sampling points
        log.info('processing noise samples')
        normal_samples = utils.aggregate_noise_values(normal_samples)
        interpolated_samples = utils.aggregate_noise_values(interpolated_samples, prefer_syke=True)

        # combine sampling point dataframes to one
        normal_samples = normal_samples[sampling_columns]
        interpolated_samples = interpolated_samples[sampling_columns]

        all_samples = pd.concat([normal_samples, interpolated_samples], ignore_index=True)

    if all_samples[S.xy_id].nunique() != len(all_samples.index):
        log.error(f'found invalid number of unique sampling point ids: {len(all_samples.index)} != {all_samples[S.xy_id].nunique()}')

    if initial_sampling_count != len(all_samples.index):
        log.error(f'found mismatch in sampling point count: {len(all_samples.index)} != {initial_sampling_count}')

    final_samples = pd.merge(point_gdf, all_samples, how='left', on=S.xy_id)

    if len(final_samples.index) != len(point_gdf.index):
        log.error(f'mismatch in row counts after merging sampled values to initial sampling points: {len(final_samples.index)} != {len(point_gdf.index)}')

    if b_debug:
        log.info('exporting sampling points to gpkg')
        final_samples_gdf = gpd.GeoDataFrame(final_samples, crs=CRS.from_epsg(3879))
        final_samples_gdf.drop(columns=[S.n_max_sources]).to_file(debug_gpkg, layer='final_noise_samples', driver='GPKG')

    edge_noises = utils.aggregate_noises_by_edge(final_samples)

    if len(edge_noises.index) != edge_gdf[S.sampling_points].count():
        log.error(f'mismatch in final aggregated noise values by edges ({len(edge_noises.index)} != {len(edge_gdf.index)})')

    log.info('all done')
    return edge_noises.rename(columns={S.edge_id: E.id_ig.name})


def get_previously_processed_max_id(csv_dir: str):
    csv_files = os.listdir(csv_dir)
    max_ids = [int(name.split('_')[0]) for name in csv_files]
    return max(max_ids) if max_ids else 0


def export_edge_noise_csv(edge_noises: pd.DataFrame, out_dir: str):
    max_id = edge_noises[E.id_ig.name].max()
    csv_name = f'{max_id}_edge_noises.csv'
    edge_noises.to_csv(out_dir + csv_name)


if __name__ == '__main__':
    graph = ig_utils.read_graphml('data/hma.graphml')
    log.info(f'read graph of {graph.ecount()} edges')
    edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig])
    edge_gdf = edge_gdf.sort_values(E.id_ig.name)

    # read noise data
    noise_layer_names = [layer for layer in fiona.listlayers('data/noise_data_processed.gpkg')]
    noise_layers = {name: gpd.read_file('data/noise_data_processed.gpkg', layer=name) for name in noise_layer_names}
    noise_layers = {name: gdf.rename(columns={'db_low': name}) for name, gdf in noise_layers.items()}
    log.info(f'read {len(noise_layers)} noise layers')

    # read nodata zone: narrow area between noise surfaces of different municipalities
    nodata_layer = gpd.read_file('data/extents.gpkg', layer='municipal_boundaries')

    # process chunks of edges together by dividing gdf to parts
    processing_size = 50000
    split_gdf_count = math.ceil(len(edge_gdf)/processing_size)
    gdfs = np.array_split(edge_gdf, split_gdf_count)

    # get max id of previously processed edges
    max_processed_id = get_previously_processed_max_id('out_csv/')
    if max_processed_id > 0:
        log.info(f'found previously processed edges up to edge id {max_processed_id}')

    for idx, gdf in enumerate(gdfs):

        if gdf[E.id_ig.name].max() <= max_processed_id:
            log.info(f'skipping {idx+1} of {len(gdfs)} edge gdfs (processed before)')
            continue
        else:
            log.info(f'processing {idx+1} of {len(gdfs)} edge gdfs')

        edge_noises = noise_graph_join(
            edge_gdf=gdf,
            sampling_interval = 3,
            noise_layers = noise_layers,
            nodata_layer = nodata_layer,
            b_debug = False,
            debug_gpkg = 'debug/noise_join_debug.gpkg'
        )
        export_edge_noise_csv(edge_noises, 'out_csv/')
