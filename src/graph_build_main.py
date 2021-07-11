import graph_build.graph_export.main as graph_export
from graph_build.graph_export.conf import conf as graph_export_conf
import graph_build.common.utils as utils
import logging
import logging.config
from graph_build.common.logging_conf import logging_conf
logging.config.dictConfig(logging_conf)


log = logging.getLogger('graph_build.main')


script_options = ['graph_noise_join', 'graph_export']
selected_script = utils.read_user_input('Which script?', script_options, True)


if selected_script == 'graph_export':
    log.info(f'Running script: {selected_script}')
    if utils.confirm_config(graph_export_conf):
        graph_export.graph_export(graph_export_conf)
