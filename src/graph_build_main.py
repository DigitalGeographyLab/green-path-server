from graph_build.graph_export.conf import conf as graph_export_conf
import graph_build.graph_export.main as graph_export
from graph_build.graph_noise_join.conf import conf as noise_graph_join_conf
import graph_build.graph_noise_join.noise_graph_join as noise_graph_join
import graph_build.graph_noise_join.noise_graph_update as noise_graph_update
import graph_build.common.utils as utils
import logging
import logging.config
from graph_build.common.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)


log = logging.getLogger('graph_build.main')


script_options = ['noise_graph_join', 'graph_noise_update', 'graph_export']
selected_script = utils.read_user_input('Which script?', script_options, True)


if selected_script:
    log.info(f'Running script: {selected_script}')


if selected_script == 'noise_graph_join':
    if utils.confirm_config(noise_graph_join_conf):
        noise_graph_join.main(noise_graph_join_conf)


if selected_script == 'graph_noise_update':
    if utils.confirm_config(noise_graph_join_conf):
        noise_graph_update.main(noise_graph_join_conf)


if selected_script == 'graph_export':
    if utils.confirm_config(graph_export_conf):
        graph_export.graph_export(graph_export_conf)
