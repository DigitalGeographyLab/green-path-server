"""
This script loads and samples static AQI data for green paths server.
It exports a CSV file with two columns: edge ID & AQI. To use the exported AQI data
in GP server, set use_mean_aqi to True in gp_server/conf.py.

This script can be run from src/ with the command:
python -m aq_data_import.import_static_aq_data
(running as a module allows the imports to work)

"""

import common.igraph as ig_utils
import aqi_updater.aq_sampling as aq_sampling
from common.igraph import Edge as E
import logging
import logging.config
from aqi_updater.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)
log = logging.getLogger('main')


graph_id = 'kumpula' # 'hma'
mean_aqi_tif = r'aq_data_import/data/yearly_2019_aqi_avg_sum.tiff'
graph_file = fr'graphs/{graph_id}.graphml'
aq_update_out_file = fr'aqi_updates/yearly_2019_aqi_avg_sum_{graph_id}.csv'
aq_attr_name = 'aqi'


graph = ig_utils.read_graphml(graph_file)
edge_point_gdf = aq_sampling.get_sampling_point_gdf_from_graph(graph)
log.info(f'Loaded {len(edge_point_gdf)} edges for AQI sampling')
sampling_gdf = edge_point_gdf.drop_duplicates(E.id_way.name)
log.info(f'Created {len(sampling_gdf)} sampling points')

aqi_sample_df = aq_sampling.sample_aq_to_point_gdf(
    sampling_gdf, 
    mean_aqi_tif,
    aq_attr_name
)

aqi_sample_df = aq_sampling.validate_aqi_sample_df(aqi_sample_df, aq_attr_name, log)

final_edge_aqi_samples = aq_sampling.merge_edge_aq_samples(
    edge_point_gdf,
    aqi_sample_df,
    aq_attr_name,
    log
)

log.info(f'Combined AQI samples for {len(final_edge_aqi_samples)} edges')

final_edge_aqi_samples.to_csv(aq_update_out_file, index=False)
log.info(f'Exported AQI update file: {aq_update_out_file}')