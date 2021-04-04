import graph_builder.common.conf as conf
import graph_builder.graph_export.main as graph_export
import graph_builder.common.utils as utils
import geopandas as gpd
import logging


log = logging.getLogger('graph_builder.main')


hel_extent = gpd.read_file(r'graph_builder/common/hel.geojson')

graph_name_options = ['kumpula', 'hma']
graph_name = utils.read_user_input('Which graph?', graph_name_options)


if graph_name:
    log.info(f'Exporting graph: {graph_name}')
    graph_export.graph_export(
        r'graph_builder/graph_export/',
        graph_name,
        hel_extent
    )
