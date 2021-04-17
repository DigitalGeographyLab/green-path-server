import logging
from common.igraph import Edge as E
from math import floor
import os
import numpy as np
import json
import geopandas as gpd
import aqi_updater.aq_sampling as aq_sampling


def get_aqi_csv_name(aqi_tif_name: str) -> str:
    return aqi_tif_name.replace('.tif', '.csv')


def get_aqi_class(aqi: float):
    """Returns AQI class identifier, that is in the range from 1 to 9. Returns 0 if the given AQI
    is invalid. AQI classes represent (9 x) 0.5 intervals in the original AQI scale from 1.0 to 5.0.
    Class ranges are 1: 1.0-1.5, 2: 1.5-2.0, 3: 2.0-2.5 etc.
    """
    return floor(aqi * 2) - 1 if np.isfinite(aqi) else 0


class AqiUpdater():

    def __init__(self, graph, aqi_cache: str, aqi_updates_dir: str):
        self.log = logging.getLogger('aqi_updater')
        self.latest_aqi_csv: str = ''
        self.__wip_aqi_csv: str = ''
        self.__edge_gdf = aq_sampling.get_sampling_point_gdf_from_graph(graph)
        self.__sampling_gdf = self.__edge_gdf.drop_duplicates(E.id_way.name)
        self.__aqi_cache = aqi_cache
        self.__aqi_updates_dir = aqi_updates_dir
        self.__status = ''

    def new_update_available(self, latest_aqi_tif_name: str) -> bool:
        """Returns False if the expected latest aqi file is either already processed or being
        processed at the moment, else returns True.
        """
        b_available = True
        status = ''
        if self.latest_aqi_csv == get_aqi_csv_name(latest_aqi_tif_name):
            status = 'Latest AQI update already done'
            b_available = False
        else:
            status = f'New AQI update available: {latest_aqi_tif_name}'
            b_available = True

        if self.__status != status:
            self.log.info(f'AQI updater status changed to: {status}')
            self.__status = status

        return b_available

    def create_aqi_update_csv(self, aqi_tif_name: str) -> None:
        self.__wip_aqi_csv = get_aqi_csv_name(aqi_tif_name)
        aqi_tif_file = fr'{self.__aqi_cache}{aqi_tif_name}'
        aqi_sample_df = aq_sampling.sample_aq_to_point_gdf(
            self.__sampling_gdf,
            aqi_tif_file,
            'aqi'
        )
        aqi_sample_df = aq_sampling.validate_aqi_sample_df(aqi_sample_df, 'aqi', self.log)
        # export sampled AQI values to json for AQI map
        self.__export_aqi_map_json(aqi_sample_df)
        # export sampled AQI values to csv
        final_edge_aqi_samples = aq_sampling.merge_edge_aq_samples(
            self.__edge_gdf,
            aqi_sample_df,
            'aqi',
            self.log
        )
        final_edge_aqi_samples.to_csv(fr'{self.__aqi_updates_dir}{self.__wip_aqi_csv}', index=False)
        self.log.info(f'Exported edge_aqi_csv: {self.__wip_aqi_csv}')
        self.latest_aqi_csv = self.__wip_aqi_csv

    def finish_aqi_update(self) -> None:
        self.__wip_aqi_csv = ''
        self.__remove_old_update_files()

    def __export_aqi_map_json(self, sample_gdf: gpd.GeoDataFrame):
        gdf = sample_gdf[[E.id_way.name, 'aqi']].copy()
        gdf = gdf[gdf['aqi'].notnull()]
        gdf['aqi_class'] = [get_aqi_class(aqi) for aqi in gdf['aqi']]
        id_aqi_pairs = list(zip(gdf[E.id_way.name].tolist(), gdf['aqi_class'].tolist()))
        with open(self.__aqi_updates_dir + 'aqi_map.json', 'w') as json_file:
            json.dump({'data': id_aqi_pairs}, json_file, separators=(',', ':'))
        self.log.info(f'Exported current AQI for map: {self.__aqi_updates_dir}aqi_map.json')

    def __remove_old_update_files(self) -> None:
        """Removes all edge_aqi_csv files older than the latest from from __aqi_updates_dir folder.
        """
        rm_count = 0
        errors = 0
        for file_n in os.listdir(self.__aqi_updates_dir):
            if file_n.endswith('.csv') and file_n != self.latest_aqi_csv:
                try:
                    os.remove(self.__aqi_updates_dir + file_n)
                    rm_count += 1
                except Exception:
                    errors += 1
                    pass
        self.log.info(f'Removed {rm_count} old edge aqi csv files')
        if errors:
            self.log.warning(f'Could not remove {errors} old edge aqi csv files')
