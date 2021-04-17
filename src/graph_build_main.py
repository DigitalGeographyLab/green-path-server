import graph_build.graph_export.main as graph_export
import graph_build.common.utils as utils
import geopandas as gpd
import logging
import logging.config
from graph_build.common.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)


log = logging.getLogger('graph_build.main')


hel_extent = gpd.read_file(r'graph_build/common/hel.geojson')

graph_name_options = ['kumpula', 'hma']
graph_name = utils.read_user_input('Which graph?', graph_name_options, True)


if graph_name:
    log.info(f'Exporting graph: {graph_name}')
    graph_export.graph_export(
        r'graph_build/graph_export/',
        graph_name,
        hel_extent
    )
